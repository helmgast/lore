import logging
import os
import re

from flask import render_template, Blueprint, current_app, g, request, abort, send_file, redirect, url_for
from slugify import slugify
from model.asset import FileAsset
from resource import ResourceHandler, ResourceRoutingStrategy, ResourceAccessPolicy, RacModelConverter, RacBaseForm, ResourceError
from model.shop import Product, Order, OrderLine, OrderStatus, Address
from flask.ext.mongoengine.wtf import model_form
from wtforms.fields import FormField, FieldList
from flask.ext.babel import lazy_gettext as _

logger = current_app.logger if current_app else logging.getLogger(__name__)

asset_app = Blueprint('assets', __name__, template_folder='../templates/asset')

file_asset_strategy = ResourceRoutingStrategy(FileAsset, 'files', 'slug', short_url=True)

ResourceHandler.register_urls(asset_app, file_asset_strategy)
