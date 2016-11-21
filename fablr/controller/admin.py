import hmac
import os
from hashlib import sha1
import re

import ipaddress
import requests
import subprocess
from flask import Blueprint
from flask import abort
from flask import json
from flask import request

from fablr.extensions import csrf

admin = Blueprint('admin', __name__, template_folder='../templates/admin')

repos = {
    "ripperdoc/MediaSorter": {
        "path": "/data/www/geneti.ca/test/",
        "key": "MyVerySecretKey",
    },
}


@csrf.exempt
@admin.route("/git_webhook", methods=['GET', 'POST'])
def git_webhook(get_json=None):
    if request.method == 'GET':
        return 'OK'
    elif request.method == 'POST':
        # Store the IP address of the requester
        request_ip = ipaddress.ip_address(u'{0}'.format(request.remote_addr))

        hook_blocks = requests.get('https://api.github.com/meta').json()['hooks']

        # Check if the POST request is from github.com
        for block in hook_blocks:
            if ipaddress.ip_address(request_ip) in ipaddress.ip_network(block):
                break  # the remote_addr is within the network range of github.
        else:
            abort(403, 'Incorrect IP')

        if request.headers.get('X-GitHub-Event') == "ping":
            return json.dumps({'msg': 'Hi!'})
        if request.headers.get('X-GitHub-Event') != "push":
            return json.dumps({'msg': "wrong event type"})

        payload = request.get_json()
        repo_meta = {
            'name': payload['repository']['name'],
            'owner': payload['repository']['owner']['name'],
        }

        repo = None
        # Try to match on branch as configured in repos.json
        match = re.match(r"refs/heads/(?P<branch>.*)", payload['ref'])
        if match:
            repo_meta['branch'] = match.groupdict()['branch']
            repo = repos.get(
                '{owner}/{name}/branch:{branch}'.format(**repo_meta), None)

        # Fallback to plain owner/name lookup
        if not repo:
            repo = repos.get('{owner}/{name}'.format(**repo_meta), None)

        if repo and repo.get('path', None):
            # Check if POST request signature is valid
            key = repo.get('key', None)
            if key:
                signature = request.headers.get('X-Hub-Signature').split('=')[1]
                if type(key) == unicode:
                    key = key.encode()
                mac = hmac.new(key, msg=request.data, digestmod=sha1)
                if not hmac.compare_digest(mac.hexdigest(), signature):
                    abort(403, "Incorrect key")

        cwd = os.path.join(repo.get('path'), '.')
        rm = subprocess.Popen(('rm', '-r', os.path.join(repo.get('path'), '*')), cwd=cwd)
        rm.wait()
        rm = subprocess.Popen(('rm', '-r', os.path.join(repo.get('path'), '.*')), cwd=cwd)
        rm.wait()

        curl = subprocess.Popen(('curl', '-L', 'https://api.github.com/repos/{owner}/{name}/tarball'.format(**repo_meta)),
                                cwd=cwd, stdout=subprocess.PIPE)
        tar = subprocess.check_output(('tar', 'xz', '--strip=1'), stdin=curl.stdout, cwd=cwd)

        return 'OK'