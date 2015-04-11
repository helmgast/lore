import logging

from flask import Blueprint, current_app, make_response, redirect, url_for, send_file, g
from mongoengine import Q
from werkzeug.exceptions import abort

from model.asset import FileAsset
from controller.resource import ResourceHandler, ResourceRoutingStrategy, ResourceAccessPolicy
from model.shop import Order, OrderStatus, products_owned_by_user
from model.user import User

logger = current_app.logger if current_app else logging.getLogger(__name__)

asset_app = Blueprint('assets', __name__, template_folder='../templates/asset')

file_asset_strategy = ResourceRoutingStrategy(FileAsset, 'files', 'slug', short_url=True,
                                              access_policy=ResourceAccessPolicy({'_default': 'admin'}),
                                              post_edit_action='list')
ResourceHandler.register_urls(asset_app, file_asset_strategy)


def _return_link(asset):
    response = make_response(asset.file_data.read())
    response.mimetype = asset.get_mimetype()
    return response


def _return_file(asset, user):
    return send_file(asset.file_data,
                     as_attachment=True,
                     attachment_filename=asset.get_user_attachment_filename(user),
                     mimetype=asset.get_mimetype())


def _validate_public_asset(fileasset):
    asset = FileAsset.objects(slug=fileasset).first_or_404()
    if not (asset.is_public() or (g.user and g.user.admin)):
        abort(403)
    if not asset.file_data_exists():
        abort(404)
    return asset


def _validate_user_asset(fileasset, user):
    user = User.objects(id=user).first_or_404()
    if user is None or not (user == g.user or g.user.admin):
        abort(401)
    asset = FileAsset.objects(slug=fileasset).first_or_404()
    if not _is_user_allowed_access_to_asset(user, asset):
        abort(403)
    if not asset.file_data_exists():
        abort(404)
    return asset, user


def _is_user_allowed_access_to_asset(user, asset):
    if asset.is_public or g.user.admin:
        return True
    for product in products_owned_by_user(user):
        if asset in product.file_assets:
            return True
    return False


@asset_app.route('/')
def index():
    return redirect(url_for('.fileasset_list'))


@asset_app.route('/link/<fileasset>')
def link(fileasset):
    return _return_link(_validate_public_asset(fileasset))


@asset_app.route('/download/<fileasset>')
def download(fileasset):
    return _return_file(_validate_public_asset(fileasset), None)


@asset_app.route('/link/<user>/<fileasset>')
def user_link(user, fileasset):
    asset, file_user = _validate_user_asset(fileasset, user)
    return _return_link(asset)


@asset_app.route('/download/<user>/<fileasset>')
def user_download(user, fileasset):
    asset, file_user = _validate_user_asset(fileasset, user)
    return _return_file(asset, file_user)


