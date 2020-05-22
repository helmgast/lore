import hmac
import ipaddress
import logging
import os
import re
import shutil
import subprocess
from hashlib import sha1

import requests
from flask import Blueprint, abort, current_app, flash, g, json, redirect, request, safe_join, url_for
from flask_babel import lazy_gettext as _
from flask_mongoengine.wtf import model_form
from mongoengine import NotUniqueError, ValidationError
from jsonrpcclient.clients.http_client import HTTPClient
from jsonrpcclient.requests import Request
from lore.api.resource import (
    ImprovedBaseForm,
    ImprovedModelConverter,
    ItemResponse,
    ListResponse,
    ResourceAccessPolicy,
    ResourceView,
    filterable_fields_parser,
)
from lore.extensions import csrf
from lore.model.world import Shortcut
from tools.import_textalk import order_default_fields_to_return, product_default_fields_to_return, rpc_get
import urllib.parse
from lore.model.shop import import_order, import_product
from sentry_sdk import capture_exception, capture_message
from tools.batch import Job

admin = Blueprint("admin", __name__)

logger = current_app.logger if current_app else logging.getLogger(__name__)


class ShortcutAccessPolicy(ResourceAccessPolicy):
    def authorize(self, op, user=None, res=None):
        # TODO temporary translation between old and new op words, e.g. patch vs edit
        op = self.translate.get(op, op)
        if not user:
            user = g.user

        if op == "list":
            return self.is_admin(op, user, res)

        if op == "new":
            if res and res.url:  # Only let admins set external URL
                return self.is_admin(op, user, res)
            else:
                return self.is_user(op, user, res)

        if op == "view":  # If list, resource refers to a parent resource
            return self.is_admin(op, user, res)

        return self.custom_auth(op, user, res)


class ShortcutsView(ResourceView):
    list_template = "world/shortcut_list.html"
    item_template = "world/shortcut_item.html"
    form_class = model_form(Shortcut, base_class=ImprovedBaseForm, converter=ImprovedModelConverter())
    access_policy = ShortcutAccessPolicy()
    model = Shortcut
    list_arg_parser = filterable_fields_parser(["created_date"])

    def index(self):
        r = ListResponse(ShortcutsView, [("shortcuts", Shortcut.objects())])
        r.auth_or_abort()
        r.prepare_query()
        return r

    def get(self, id):
        if id == "post":
            r = ItemResponse(ShortcutsView, [("shortcut", None)], extra_args={"intent": "post"})
            r.auth_or_abort(res=None)
        else:
            shortcut = Shortcut.objects(slug=id).first_or_404()
            r = ItemResponse(ShortcutsView, [("shortcut", shortcut)])
            r.auth_or_abort()
        return r

    def post(self):
        r = ItemResponse(ShortcutsView, [("shortcuts", None)], method="post")
        shortcut = Shortcut()
        if not r.validate():
            return r.error_response(status=400)
        r.form.populate_obj(shortcut)
        r.auth_or_abort(res=shortcut)
        try:
            r.commit(new_instance=shortcut)
        except NotUniqueError as err:
            flash(_("Short URL already in use"))
            return r, 400
        except ValidationError as err:
            return r.error_response(err)
        if shortcut.article:
            shortcut.article.shortcut = shortcut
            shortcut.article.save()
        return redirect(r.args["next"] or url_for("admin.ShortcutsView:get", id=shortcut.slug))


ShortcutsView.register_with_access(admin, "shortcut")


@csrf.exempt
@admin.route("/import_textalk/<model>", methods=["POST"])
def import_webhook(model):
    f = request.form
    # Expected formdata body: class=Order&event=discarded&uid=156748351&webshop=49251
    event_class = f.get("class", None)
    event_name = f.get("event", None)
    webshop = f.get("webshop", None)
    uid = f.get("uid")
    publisher = "helmgast.se"  # TODO this is currently locked to one publisher

    if (
        model.lower() == "order"
        and event_class == "Order"
        and event_name == "paid"
        and webshop in current_app.config["TEXTALK_URL"]
        and uid
    ):
        try:
            data = rpc_get("Order.get", uid, order_default_fields_to_return)
            data["publisher"] = publisher
            data["title"] = "Webshop"
            data["sourceUrl"] = "https://webshop.helmgast.se"
            job = Job()
            order = import_order(data, job=job, commit=True)
            if order is not None:
                logger.info(f"Imported {order!r} from {uid}, {job}")
            else:
                logger.info(f"Skipped importing order {uid}, {job}")
            return "OK", 200
        except Exception as e:
            logger.error(e)
            capture_exception(e)
    elif (
        model.lower() == "product"
        and event_class == "Article"
        and event_name == "created"
        or event_name == "changed"
        and webshop in current_app.config["TEXTALK_URL"]
        and uid
    ):
        try:
            data = rpc_get("Article.get", uid, product_default_fields_to_return)
            data["publisher"] = publisher
            job = Job()
            product = import_product(data, job=job, commit=True)
            if product is not None:
                logger.info(f"Imported {product!r} from {uid}, {job}")
            else:
                logger.info(f"Skipped importing product {uid}, {job}")
            return "OK", 200
        except Exception as e:
            logger.error(e)
            capture_exception(e)
    else:
        msg = f"Incorrect event data received: {request.data}"
        logger.error(msg)
        capture_message(msg)
        abort(400, msg)


@csrf.exempt
@admin.route("/git_webhook", methods=["GET", "POST"])
def git_webhook(get_json=None):
    if request.method == "GET":
        return "OK"
    elif request.method == "POST":
        # Store the IP address of the requester
        request_ip = ipaddress.ip_address(str(request.remote_addr))

        hook_blocks = requests.get("https://api.github.com/meta").json()["hooks"]

        # Check if the POST request is from github.com
        if not current_app.debug:
            for block in hook_blocks:
                if ipaddress.ip_address(request_ip) in ipaddress.ip_network(block):
                    # the remote_addr is within the network range of github.
                    break
            else:
                logger.warning(
                    "git_webhook: Incorrect IP: %s not in %s"
                    % (ipaddress.ip_address(request_ip), ipaddress.ip_network(block))
                )
                abort(403, f"Incorrect IP {request_ip}")

        if request.headers.get("X-GitHub-Event") == "ping":
            return json.dumps({"msg": "Hi!"})
        if request.headers.get("X-GitHub-Event") != "push":
            logger.warning("git_webhook: Wrong event type")
            return json.dumps({"msg": "wrong event type"}), 400

        payload = request.get_json()
        try:
            # Replace path components although they shouldn't be here
            repo_meta = {
                "name": re.sub(r"[./]", "", payload["repository"]["name"]),
                "owner": re.sub(r"[./]", "", payload["repository"]["owner"]["name"]),
                "commit": payload.get("after", None),
            }
            if "name" not in repo_meta or "owner" not in repo_meta:
                raise TypeError("No name or owner in repo_meta")
        except TypeError as te:
            logger.error("Malformed JSON for git_webhook: {payload}".format(payload=payload))
            return json.dumps({"msg": "Malformed JSON for git_webhook"}), 400

        # Try to match on branch as configured in repos.json
        match = re.match(r"refs/heads/(?P<branch>.+)", payload["ref"])
        if match:
            repo_meta["branch"] = re.sub(r"[./]", "", match.groupdict()["branch"])
            path = "{owner}/{name}/branch_{branch}".format(**repo_meta)
        else:
            path = "{owner}/{name}".format(**repo_meta)

        key = current_app.config.get("GITHUB_WEBHOOK_KEY", None).encode()
        # Check if POST request signature is valid
        if not key:
            logger.warning("git_webhook: No key configured")
            return json.dumps({"msg": "No key configured"}), 403

        signature = request.headers.get("X-Hub-Signature").split("=")[1]
        # if type(key) == unicode:
        #     key = key.encode()
        # Input to hmac.new need to be bytes, but compare_digest can compare str
        mac = hmac.new(key, msg=request.data, digestmod=sha1)
        if not hmac.compare_digest(mac.hexdigest(), signature):
            logger.warning("git_webhook: Incorrect key")
            return json.dumps({"msg": "Incorrect key"}), 403

        # We will create a subdir to /data/www/github and operate on that
        # It will not be reachable from web unless configured in other web server

        cwd = safe_join(current_app.config["PLUGIN_PATH"], path)
        # Delete directory to get clean copy
        shutil.rmtree(cwd, ignore_errors=True)
        os.makedirs(cwd)  # Make all dirs necessary for this path
        try:
            curl = subprocess.Popen(
                ("curl", "-Ls", "https://api.github.com/repos/{owner}/{name}/tarball".format(**repo_meta)),
                cwd=cwd,
                stdout=subprocess.PIPE,
            )
            tar = subprocess.check_output(("tar", "xz", "--strip=1"), stdin=curl.stdout, cwd=cwd)
        except subprocess.CalledProcessError as cpe:
            logger.warning("Error fetching repo for {data}, got {out}".format(data=repo_meta, out=cpe.output))
            return json.dumps({"msg": "Error fetching repo"}), 403
        return "OK commit {commit} to {path}".format(path=path, **repo_meta)

