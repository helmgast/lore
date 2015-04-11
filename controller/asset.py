import logging

from flask import Blueprint, current_app, make_response, redirect, url_for, send_file
from werkzeug.exceptions import abort

from model.asset import FileAsset
from controller.resource import ResourceHandler, ResourceRoutingStrategy

logger = current_app.logger if current_app else logging.getLogger(__name__)

asset_app = Blueprint('assets', __name__, template_folder='../templates/asset')

file_asset_strategy = ResourceRoutingStrategy(FileAsset, 'files', 'slug', short_url=True, post_edit_action='list')
ResourceHandler.register_urls(asset_app, file_asset_strategy)


@asset_app.route('/')
def index():
    return redirect(url_for('.fileasset_list'))


@asset_app.route('/link/<fileasset>')
def link(fileasset):
    asset = FileAsset.objects(slug=fileasset).first_or_404()
    if not asset.file_data_exists:
        abort(404)
    response = make_response(asset.file_data.read())
    response.mimetype = asset.get_mimetype()
    return response


@asset_app.route('/download/<fileasset>')
def download(fileasset):
    asset = FileAsset.objects(slug=fileasset).first_or_404()
    if not asset.file_data_exists:
        abort(404)
    return send_file(asset.file_data,
                     as_attachment=True,
                     attachment_filename=asset.get_attachment_filename(),
                     mimetype=asset.get_mimetype())

