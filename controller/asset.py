import logging

from flask import Blueprint, current_app, make_response

from model.asset import FileAsset
from controller.resource import ResourceHandler, ResourceRoutingStrategy

logger = current_app.logger if current_app else logging.getLogger(__name__)

asset_app = Blueprint('assets', __name__, template_folder='../templates/asset')

file_asset_strategy = ResourceRoutingStrategy(FileAsset, 'files', 'slug', short_url=True)
ResourceHandler.register_urls(asset_app, file_asset_strategy)

@asset_app.route('/fetch/<slug>')
def fetch_asset(slug):
    asset = FileAsset.objects(slug=slug).first_or_404()
    response = make_response(asset.file_data.read())
    response.mimetype = asset.get_mimetype()
    return response

