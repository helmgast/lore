from flask import request, redirect, url_for, render_template, Blueprint, flash
from model.world import Article, World, ArticleRelation, PersonArticle, PlaceArticle, EventArticle, MediaArticle, FractionArticle, ARTICLE_DEFAULT, ARTICLE_MEDIA, ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT, ARTICLE_TYPES
from model.user import Group
from flask.views import View

from resource import ResourceHandler2, ResourceAccessStrategy
from raconteur import auth
from itertools import groupby
from datetime import datetime, timedelta
from wtforms.fields import FieldList, HiddenField
from werkzeug.datastructures import ImmutableMultiDict

world_app = Blueprint('world', __name__, template_folder='templates')

world_handler = ResourceHandler2(ResourceAccessStrategy(World, 'worlds'))
world_handler.register_urls(world_app)

article_handler = ResourceHandler2(ResourceAccessStrategy(Article, 'articles', parent_strategy=world_handler.strategy))
article_handler.register_urls(world_app)


@world_app.route('/')
def index():
    qr = World.objects()
    return render_template('world/base.html', qr)


# Template filter, will group a list by their initial title letter
def by_initials(objects):
  groups = []
  for k, g in groupby(objects, lambda o: o.title[0:1]):
    groups.append({'grouper':k, 'list':list(g)})
  return groups

# Template filter, will group a list by their article type_name
def by_articletype(objects):
  groups = []
  for k, g in groupby(objects, lambda o: o.type_name()):
    groups.append({'grouper':k, 'list':list(g)})
  return groups

def prettydate(d):
    diff = timedelta()
    diff = datetime.utcnow() - d
    if diff.days < 1:
        return 'Today'
    elif diff.days < 7:
        return 'Last week'
    elif diff.days < 31:
        return 'Last month'
    elif diff.days < 365:
        return 'Last year'
    else:
        return 'Older'

# Template filter, will group a list by creation date, as measure in delta from now
def by_time(objects):
  groups = []
  for k, g in groupby(objects, lambda o: prettydate(o.created_date)):
    groups.append({'grouper':k, 'list':list(g)})
  return groups

world_app.add_app_template_filter(by_initials)
world_app.add_app_template_filter(by_articletype)
world_app.add_app_template_filter(by_time)