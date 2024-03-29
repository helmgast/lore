import io
import logging
from time import time
from urllib.parse import quote

import pyqrcode
from flask import Blueprint, current_app, redirect, url_for, g, request, Response, flash, send_file
from flask_babel import lazy_gettext as _
from flask_mongoengine.wtf import model_form
from mongoengine import NotUniqueError, ValidationError
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
from flask_classy import route

from lore.api.pdf import fingerprint_pdf
from lore.api.resource import (
    Authorization,
    FilterableFields,
    ImprovedBaseForm,
    ImprovedModelConverter,
    ItemResponse,
    ListResponse,
    ResourceAccessPolicy,
    ResourceView,
    filterable_fields_parser,
    prefillable_fields_parser,
    set_theme,
)

from lore.model.asset import FileAccessType, FileAsset, get_google_urls
from lore.model.misc import set_lang_options, filter_is_owner
from lore.model.shop import products_owned_by_user, user_has_asset
from lore.model.world import Publisher, filter_authorized_by_publisher

logger = current_app.logger if current_app else logging.getLogger(__name__)

asset_app = Blueprint("assets", __name__)


def set_cache(rv, cache_timeout):
    if cache_timeout is not None:
        rv.cache_control.public = True
        rv.cache_control.max_age = cache_timeout
        rv.expires = int(time() + cache_timeout)
    return rv


# Inspiration
# https://github.com/RedBeard0531/python-gridfs-server/blob/master/gridfs_server.py
def send_gridfs_file(
    gridfile,
    mimetype=None,
    as_attachment=False,
    attachment_filename=None,
    add_etags=True,
    cache_timeout=2628000,
    conditional=True,
    fingerprint_user_id=None,
):
    # Default cache timeout is 1 month in seconds
    if not mimetype:
        if not gridfile.content_type:
            raise ValueError("No Mimetype given and none in the gridfile")
        mimetype = gridfile.content_type

    # TODO check that this is in UTC-time
    headers = {
        "Content-Length": gridfile.length,
        "Last-Modified": gridfile.upload_date.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    }  #
    if as_attachment:
        if not attachment_filename:
            if not gridfile.name:
                raise ValueError("No attachment file name given and none in the gridfile")
            attachment_filename = gridfile.name
        # Handles unicode filenames in most browsers, see
        # https://stackoverflow.com/questions/21818855/flask-handling-unicode-text-with-werkzeug/30953380#30953380
        headers["Content-Disposition"] = "attachment; filename*=UTF-8''{quoted_filename}".format(
            quoted_filename=quote(attachment_filename.encode("utf8"))
        )
    md5 = gridfile.md5  # as we may overwrite gridfile with own iterator, save this
    if fingerprint_user_id:
        gridfile = fingerprint_pdf(gridfile, fingerprint_user_id)
    rv = Response(gridfile, headers=headers, content_type=mimetype, direct_passthrough=True)  # is an iterator
    set_cache(rv, cache_timeout)
    if add_etags:
        rv.set_etag(md5)
    if conditional:
        rv.make_conditional(request)
    return rv


def authorize_and_return(fileasset_slug, as_attachment=False):
    asset = FileAsset.objects(slug=fileasset_slug).first_or_404()
    publisher = Publisher.objects(slug=g.pub_host).first()
    if publisher:
        # For better error pages
        set_theme(g, "publisher", publisher.theme)

    if asset.file_data_exists():
        attachment_filename = asset.get_attachment_filename() if as_attachment else None
        mime = asset.get_mimetype()

        if asset.is_public():
            rv = send_gridfs_file(
                asset.file_data.get(),
                mimetype=mime,
                as_attachment=as_attachment,
                attachment_filename=attachment_filename,
            )
            return rv

        # If we come this far the file is private to a user and should not be cached
        # by any proxies
        if not g.user:
            # Should be caught by error handler in app.py that does SSO redirect if applicable
            abort(401)

        if g.user.admin or user_has_asset(g.user, asset):

            # A pdf that should be unique per user - we need to fingerprint it
            if mime == "application/pdf" and asset.access_type == FileAccessType.user:
                fpid = g.user.id
            else:
                fpid = None
            rv = send_gridfs_file(
                asset.file_data.get(),
                mimetype=mime,
                as_attachment=as_attachment,
                attachment_filename=attachment_filename,
                fingerprint_user_id=fpid,
            )
            # rv.headers['Cache-Control'] = 'private'  # Override the public cache
            return rv
    elif asset.source_file_url:
        return_url = asset.source_file_url
        google_urls = get_google_urls(asset.source_file_url)
        if google_urls:
            return_url = google_urls["dl"] if as_attachment else google_urls["direct"]
        if asset.is_public():
            return redirect(return_url)
        if not g.user:
            # Should be caught by error handler in app.py that does SSO redirect if applicable
            abort(401)
        if g.user.admin or user_has_asset(g.user, asset):
            return redirect(return_url)
    abort(403)


class AssetAccessPolicy(ResourceAccessPolicy):
    def is_editor(self, op, user, res):
        if user == res.owner or (res.publisher and user in res.publisher.editors):
            return Authorization(
                True, _('Allowed access to %(op)s "%(res)s" as editor', op=op, res=res), privileged=True
            )
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not an editor', op=op, res=res))

    def is_reader(self, op, user, res):
        if user == res.owner or (res.publisher and user in res.publisher.readers):
            return Authorization(
                True, _('Allowed access to %(op)s "%(res)s" as reader', op=op, res=res), privileged=True
            )
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not a reader', op=op, res=res))


class FileAssetsView(ResourceView):
    subdomain = "<pub_host>"
    route_base = "/media/"
    access_policy = AssetAccessPolicy()
    model = FileAsset
    list_template = "asset/fileasset_list.html"
    item_template = "asset/fileasset_item.html"
    form_class = model_form(
        FileAsset,
        exclude=["md5", "source_filename", "length", "created_date", "content_type", "width", "height", "file_data"],
        base_class=ImprovedBaseForm,
        converter=ImprovedModelConverter(),
    )
    filterable_fields = FilterableFields(
        FileAsset,
        [
            ("slug", _("File")),
            "owner",
            "access_type",
            "content_type",
            "tags",
            "length",
            ("publisher.title", FileAsset.publisher.verbose_name),
        ],
        choice=lambda x: x if x in ["single", "multiple"] else "multiple",
        select=lambda x: x.split(","),
        position=lambda x: x if x in ["gallery-center", "gallery-card", "gallery-wide"] else "gallery-center",
    )

    item_arg_parser = prefillable_fields_parser(["slug", "owner", "access_type", "tags", "length"])

    def index(self, **kwargs):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        r = ListResponse(
            FileAssetsView,
            [("files", FileAsset.objects().order_by("-created_date")), ("publisher", publisher)],
            extra_args=kwargs,
        )
        r.set_theme("publisher", publisher.theme if publisher else None)
        r.auth_or_abort()

        if not (g.user and g.user.admin):
            r.query = r.query.filter(filter_is_owner() | filter_authorized_by_publisher(publisher))

        r.finalize_query()

        # This will re-order so that any selected files are guaranteed to show first
        if r.args["select"] and len(r.args["select"]) > 0:
            head, tail = [], []
            for item in r.files:
                if item.slug in r.args["select"]:
                    head.append(item)
                else:
                    tail.append(item)
            r.files = head + tail

        return r

    @route("<path:id>", methods=["GET"])
    def get(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        if id == "post":
            r = ItemResponse(FileAssetsView, [("fileasset", None)], extra_args={"intent": "post"})
            r.set_theme("publisher", publisher.theme if publisher else None)
            r.auth_or_abort(res=None)
        else:
            fileasset = FileAsset.objects(slug=id).first_or_404()
            r = ItemResponse(FileAssetsView, [("fileasset", fileasset)])
            r.set_theme("publisher", publisher.theme if publisher else None)
            r.auth_or_abort()
        return r

    @route("<path:id>", methods=["PATCH"])
    def patch(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        fileasset = FileAsset.objects(slug=id).first_or_404()

        r = ItemResponse(FileAssetsView, [("fileasset", fileasset)], method="patch")
        r.set_theme("publisher", publisher.theme if publisher else None)
        r.auth_or_abort()

        if not r.validate():
            # return same page but with form errors?
            flash(_("Error in form"), "danger")
            return r, 400  # BadRequest
        # only populate selected keys. will skip empty selects!
        r.form.populate_obj(fileasset)
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args["next"] or url_for("assets.FileAssetsView:get", id=fileasset.slug))

    def post(self):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        r = ItemResponse(FileAssetsView, [("fileasset", None)], method="post")
        r.set_theme("publisher", publisher.theme if publisher else None)
        r.auth_or_abort()

        fileasset = FileAsset()
        if not r.validate():
            flash(_("Error in form"), "danger")
            return r, 400
        r.form.populate_obj(fileasset)
        try:
            r.commit(new_instance=fileasset)
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args["next"] or url_for("assets.FileAssetsView:get", id=fileasset.slug))

    def file_selector(self, type):
        kwargs = {
            "out": "modal",
            "intent": "patch",
            "view": "card",
        }
        if type == "image":
            kwargs["content_type__startswith"] = "image/"
        elif type == "document":
            kwargs["content_type__not__startswith"] = "image/"
        elif type == "any":
            pass  # no content_type requirement
        else:
            abort(404)
        r = self.index(**kwargs)
        return r

    @route("<path:id>", methods=["DELETE"])
    def delete(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)
        fileasset = FileAsset.objects(slug=id).first_or_404()
        r = ItemResponse(FileAssetsView, [("fileasset", fileasset)], method="delete")
        r.auth_or_abort()
        r.commit()
        return redirect(r.args["next"] or url_for("assets.FileAssetsView:index", pub_host=publisher.slug))


FileAssetsView.register_with_access(asset_app, "files")


@asset_app.route("/", subdomain="<pub_host>")
def index():
    return redirect(url_for("assets.FileAssetsView:index"))


@current_app.route("/asset/link/<path:fileasset>")
def link(fileasset):
    return authorize_and_return(fileasset)


@current_app.route("/asset/qr/<code>.svg")
def qrcode(code):
    host = current_app.config["DEFAULT_HOST"].upper()
    code = code.upper()
    # Uppercase letters give a more compact QR code
    qr = pyqrcode.create(f"HTTPS://{host}/+{code}", error="L")
    out = io.BytesIO()
    qr.svg(out, scale=5)
    out.seek(0)
    return send_file(out, attachment_filename="qrcode.svg", mimetype="image/svg+xml")


@current_app.route("/asset/download/<path:fileasset>")
def download(fileasset):
    return authorize_and_return(fileasset, as_attachment=True)


@current_app.route("/asset/image/<path:slug>")
def image(slug):
    asset = FileAsset.objects(slug=slug).first_or_404()
    if asset.content_type and asset.content_type.startswith("image/"):
        grid_file = asset.file_data.get() if asset.file_data else None
        if grid_file:
            r = send_gridfs_file(grid_file, mimetype=asset.content_type)
        else:
            abort(404)
    else:
        r = redirect(url_for("static", filename="img/icon/%s-icon.svg" % secure_filename(asset.content_type)))
        # Redirect default uses 302 temporary redirect, but we want to cache it for a while
        set_cache(r, 10)  # 10 seconds, should be 2628000 = 1 month
    return r


@current_app.route("/asset/image/thumbs/<path:slug>")
def image_thumb(slug):
    return image(slug.lower())  # thumbs temporarily out of play
    # asset = FileAsset.objects(slug=slug).first_or_404()
    # return send_gridfs_file(asset.file_data.thumbnail, mimetype=asset.content_type)
