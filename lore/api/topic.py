import logging

from flask import Blueprint, current_app
from lore.extensions import csrf

logger = current_app.logger if current_app else logging.getLogger(__name__)

topic_app = Blueprint('topic', __name__)


csrf.exempt(topic_app)
