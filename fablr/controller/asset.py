import logging
from time import time

from flask import Blueprint, current_app, redirect, url_for, g, request, Response
from flask.ext.mongoengine.wtf import model_form
from werkzeug.exceptions import abort

from fablr.controller.pdf import fingerprint_pdf
from fablr.controller.resource import ResourceHandler, ResourceRoutingStrategy, RacModelConverter, \
    ResourceAccessPolicy, ResourceError
from fablr.model.asset import FileAsset, FileAccessType, ImageAsset
from fablr.model.shop import products_owned_by_user

logger = current_app.logger if current_app else logging.getLogger(__name__)

asset_app = Blueprint('assets', __name__, template_folder='../templates/asset')

file_asset_strategy = ResourceRoutingStrategy(FileAsset, 'files', 'slug',
                                              access_policy=ResourceAccessPolicy({
                                                  #   'view': 'private', # Add these later to allow personal files
                                                  #   'edit': 'private',
                                                  #   'form_edit': 'private',
                                                  #   'replace': 'private',
                                                  #   'delete': 'private',
                                                  '_default': 'admin'
                                              }),
                                              post_edit_action='list')
ResourceHandler.register_urls(asset_app, file_asset_strategy)


# Inspiration
# https://github.com/RedBeard0531/python-gridfs-server/blob/master/gridfs_server.py
def send_gridfs_file(gridfile, mimetype=None, as_attachment=False,
                     attachment_filename=None, add_etags=True,
                     cache_timeout=2628000, conditional=True, fingerprint_user_id=None):
    # Default cache timeout is 1 month in seconds
    if not mimetype:
        if not gridfile.content_type:
            raise ValueError("No Mimetype given and none in the gridfile")
        mimetype = gridfile.content_type

    headers = {'Content-Length': gridfile.length,
               'Last-Modified': gridfile.upload_date.strftime("%a, %d %b %Y %H:%M:%S GMT")}  #
    if as_attachment:
        if not attachment_filename:
            if not gridfile.name:
                raise ValueError("No attachment file name given and none in the gridfile")
            attachment_filename = gridfile.name
        headers['Content-Disposition'] = 'attachment; filename=%s' % attachment_filename
    md5 = gridfile.md5  # as we may overwrite gridfile with own iterator, save this
    if fingerprint_user_id:
        gridfile = fingerprint_pdf(gridfile, fingerprint_user_id)
    rv = Response(
        gridfile,  # is an iterator
        headers=headers,
        content_type=mimetype,
        direct_passthrough=True)
    if cache_timeout is not None:
        rv.cache_control.public = True
        rv.cache_control.max_age = cache_timeout
        rv.expires = int(time() + cache_timeout)
    if add_etags:
        rv.set_etag(md5)
    if conditional:
        rv.make_conditional(request)
    return rv


def authorize_and_return(fileasset_slug, as_attachment=False):
    asset = FileAsset.objects(slug=fileasset_slug).first_or_404()
    if not asset.file_data_exists():
        abort(404)

    attachment_filename = asset.get_attachment_filename() if as_attachment else None
    mime = asset.get_mimetype()

    if asset.is_public():
        rv = send_gridfs_file(asset.file_data.get(), mimetype=mime,
                              as_attachment=as_attachment, attachment_filename=attachment_filename)
        return rv

    # If we come this far the file is private to a user and should not be cached
    # by any proxies
    if not g.user:
        abort(403)

    # List comprehensions are hard - here is the foor loop below would be
    # assets = []
    # for p in products_owned_by_user(g.user):
    #     for a in p.downloadable_files:
    #         assets.append(a)
    if g.user.admin or asset in [a for p in products_owned_by_user(g.user) for a in p.downloadable_files]:
        # A pdf that should be unique per user - we need to fingerprint it
        if mime == 'application/pdf' and asset.access_type == FileAccessType.user:
            fpid = g.user.id
        else:
            fpid = None
        rv = send_gridfs_file(asset.file_data.get(), mimetype=mime, as_attachment=as_attachment,
                              attachment_filename=attachment_filename, fingerprint_user_id=fpid)
        rv.headers['Cache-Control'] = 'private'  # Override the public cache
        return rv
    abort(403)


imageasset_strategy = ResourceRoutingStrategy(
    ImageAsset, 'images', form_class=
    model_form(ImageAsset, exclude=['image', 'mime_type', 'slug'], converter=RacModelConverter())
)


class ImageAssetHandler(ResourceHandler):
    def new(self, r):
        '''Override new() to do some custom file pre-handling'''
        self.strategy.authorize(r['op'])
        form = self.form_class(request.form, obj=None)
        print request.form
        # del form.slug # remove slug so it wont throw errors here
        if not form.validate():
            r['form'] = form
            raise ResourceError(400, r)
        file = request.files.get('imagefile', None)
        item = ImageAsset(creator=g.user)
        if file:
            item.make_from_file(file)
        elif request.form.has_key('source_image_url'):
            item.make_from_url(request.form['source_image_url'])
        else:
            abort(403)
        form.populate_obj(item)
        item.save()
        r['item'] = item
        r['next'] = url_for('image', slug=item.slug)
        return r


ImageAssetHandler.register_urls(asset_app, imageasset_strategy)


@asset_app.route('/')
def index():
    return redirect(url_for('.fileasset_list'))


@current_app.route('/asset/link/<fileasset>')
def link(fileasset):
    return authorize_and_return(fileasset)


@current_app.route('/asset/download/<fileasset>')
def download(fileasset):
    return authorize_and_return(fileasset, as_attachment=True)


@current_app.route('/asset/image/<slug>')
def image(slug):
    asset = ImageAsset.objects(slug=slug).first_or_404()
    r = send_gridfs_file(asset.image.get(), mimetype=asset.mime_type)
    return r


@current_app.route('/asset/image/thumbs/<slug>')
def image_thumb(slug):
    asset = ImageAsset.objects(slug=slug).first_or_404()
    return send_gridfs_file(asset.image.thumbnail, mimetype=asset.mime_type)
