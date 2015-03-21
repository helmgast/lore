import logging

from flask import Blueprint, current_app

from model.asset import FileAsset
from resource import ResourceHandler, ResourceRoutingStrategy

logger = current_app.logger if current_app else logging.getLogger(__name__)

asset_app = Blueprint('assets', __name__, template_folder='../templates/asset')

file_asset_strategy = ResourceRoutingStrategy(FileAsset, 'files', 'slug', short_url=True)
ResourceHandler.register_urls(asset_app, file_asset_strategy)
