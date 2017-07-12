from builtins import str
import hmac
import logging
import os
from hashlib import sha1
import re

import ipaddress
import requests
import subprocess

import shutil
from flask import Blueprint
from flask import abort
from flask import current_app
from flask import json
from flask import request
from flask import safe_join

from fablr.api.resource import ResourceView, ResourceAccessPolicy, RacModelConverter, RacBaseForm, ListResponse
from fablr.extensions import csrf
from flask_mongoengine.wtf import model_form

from fablr.model.world import Shortcut

admin = Blueprint('admin', __name__, template_folder='../templates/admin')

logger = current_app.logger if current_app else logging.getLogger(__name__)


class ShortcutsView(ResourceView):
    list_template = 'world/shortcut_list.html'
    item_template = 'world/shortcut_item.html'
    form_class = model_form(Shortcut, base_class=RacBaseForm, converter=RacModelConverter())
    access_policy = ResourceAccessPolicy()
    model = Shortcut

    def index(self):
        r = ListResponse(ShortcutsView, [('shortcuts', Shortcut.objects())])
        r.auth_or_abort()
        return r

ShortcutsView.register_with_access(admin, 'shortcut')


@csrf.exempt
@admin.route("/git_webhook", methods=['GET', 'POST'])
def git_webhook(get_json=None):
    if request.method == 'GET':
        return 'OK'
    elif request.method == 'POST':
        # Store the IP address of the requester
        request_ip = ipaddress.ip_address(str(request.remote_addr))

        hook_blocks = requests.get('https://api.github.com/meta').json()['hooks']

        # Check if the POST request is from github.com
        for block in hook_blocks:
            if ipaddress.ip_address(request_ip) in ipaddress.ip_network(block):
                break  # the remote_addr is within the network range of github.
        else:
            logger.warning('git_webhook: Incorrect IP: %s not in %s' % (ipaddress.ip_address(request_ip), ipaddress.ip_network(block)))
            abort(403, 'Incorrect IP')

        if request.headers.get('X-GitHub-Event') == "ping":
            return json.dumps({'msg': 'Hi!'})
        if request.headers.get('X-GitHub-Event') != "push":
            logger.warning('git_webhook: Wrong event type')
            return json.dumps({'msg': "wrong event type"}), 400

        payload = request.get_json()
        try:
            # Replace path components although they shouldn't be here
            repo_meta = {
                'name': re.sub(r'[./]', '', payload['repository']['name']),
                'owner': re.sub(r'[./]', '', payload['repository']['owner']['name']),
                'commit': payload.get('after', None)
            }
            if 'name' not in repo_meta or 'owner' not in repo_meta:
                raise TypeError("No name or owner in repo_meta")
        except TypeError as te:
            logger.error("Malformed JSON for git_webhook: {payload}".format(payload=payload))
            return json.dumps({'msg': "Malformed JSON for git_webhook"}), 400

        # Try to match on branch as configured in repos.json
        match = re.match(r"refs/heads/(?P<branch>.+)", payload['ref'])
        if match:
            repo_meta['branch'] = re.sub(r'[./]', '', match.groupdict()['branch'])
            path = '{owner}/{name}/branch_{branch}'.format(**repo_meta)
        else:
            path = '{owner}/{name}'.format(**repo_meta)

        key = current_app.config.get('GITHUB_WEBHOOK_KEY', None)
        # Check if POST request signature is valid
        if not key:
            logger.warning('git_webhook: No key configured')
            return json.dumps({'msg': "No key configured"}), 403

        signature = request.headers.get('X-Hub-Signature').split('=')[1].encode()
        # if type(key) == unicode:
        #     key = key.encode()
        mac = hmac.new(key, msg=request.data.encode(), digestmod=sha1)
        if not hmac.compare_digest(mac.hexdigest(), signature):
            logger.warning('git_webhook: Incorrect key')
            return json.dumps({'msg': "Incorrect key"}), 403

        # We will create a subdir to /data/www/github and operate on that
        # It will not be reachable from web unless configured in other web server

        cwd = safe_join(current_app.config['PLUGIN_PATH'], path)
        shutil.rmtree(cwd, ignore_errors=True)  # Delete directory to get clean copy
        os.makedirs(cwd)  # Make all dirs necessary for this path
        try:
            curl = subprocess.Popen(('curl', '-Ls', 'https://api.github.com/repos/{owner}/{name}/tarball'
                                     .format(**repo_meta)),
                                    cwd=cwd, stdout=subprocess.PIPE)
            tar = subprocess.check_output(('tar', 'xz', '--strip=1'), stdin=curl.stdout, cwd=cwd)
        except subprocess.CalledProcessError as cpe:
            logger.warning('Error fetching repo for {data}, got {out}'.format(data=repo_meta, out=cpe.output))
            return json.dumps({'msg': "Error fetching repo"}), 403
        return 'OK commit {commit} to {path}'.format(path=path, **repo_meta)
