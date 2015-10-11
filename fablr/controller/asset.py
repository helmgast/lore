import logging

from flask import Blueprint, current_app, make_response, redirect, url_for, send_file, g, Response, after_this_request
from mongoengine import Q
from werkzeug.exceptions import abort
from flask.ext.mongoengine.wtf import model_form

from fablr.model.asset import FileAsset, FileAccessType, ImageAsset
from fablr.controller.resource import ResourceHandler, ResourceRoutingStrategy, RacModelConverter, ResourceAccessPolicy
from fablr.model.shop import Order, OrderStatus, products_owned_by_user
from fablr.model.user import User
from fablr.controller.pdf import fingerprint_pdf


logger = current_app.logger if current_app else logging.getLogger(__name__)

asset_app = Blueprint('assets', __name__, template_folder='../templates/asset')

file_asset_strategy = ResourceRoutingStrategy(FileAsset, 'files', 'slug', short_url=True,
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

def _return_file(asset, as_attachment=False):
    mime = asset.get_mimetype()
    if as_attachment:
        attachment_filename=asset.get_attachment_filename()
    else:
        attachment_filename=None
    if mime == 'application/pdf' and asset.access_type == FileAccessType.user:
        if not g.user:
            abort(403)
        # A pdf that should be unique per user - we need to fingerprint it
        response = Response(
            fingerprint_pdf(asset.file_data.get(), g.user.id),
            mimetype=mime,
            direct_passthrough=True)
        # TODO Unicode filenames may break this
        response.headers['Content-Disposition'] = 'attachment; filename=%s' % attachment_filename
        return response
    else:
        return send_file(asset.file_data,
                     as_attachment=as_attachment,
                     attachment_filename=attachment_filename,
                     mimetype=mime)

def authorize_file_data(fileasset_slug):
    asset = FileAsset.objects(slug=fileasset_slug).first_or_404()

    if not asset.file_data_exists():
        abort(404)
    if asset.is_public():
        return asset

    # If we come this far the file is private to a user and should not be cached
    # by any proxies
    @after_this_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'private'
        return response

    if g.user.admin:
        return asset

    for product in products_owned_by_user(g.user):
        if asset in product.downloadable_files:
            return asset
    abort(403)

imageasset_strategy = ResourceRoutingStrategy(ImageAsset, 'images', form_class=
model_form(ImageAsset, exclude=['image','mime_type', 'slug'], converter=RacModelConverter()))
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
    asset = authorize_file_data(fileasset)
    return _return_file(asset)

@current_app.route('/asset/download/<fileasset>')
def download(fileasset):
    asset = authorize_file_data(fileasset)
    return _return_file(asset, True)

@current_app.route('/asset/image/<slug>')
def image(slug):
    asset = ImageAsset.objects(slug=slug).first_or_404()
    return send_file(asset.image, mimetype=asset.mime_type)

@current_app.route('/asset/image/thumbs/<slug>')
def image_thumb(slug):
    asset = ImageAsset.objects(slug=slug).first_or_404()
    response = make_response(asset.image.thumbnail.read())
    response.mimetype = asset.mime_type
    return response
