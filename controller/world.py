from flask import request, redirect, url_for, render_template, Blueprint, flash, make_response, g
from model.world import (Article, World, ArticleRelation, PersonArticle, PlaceArticle, 
  EventArticle, ImageArticle, FractionArticle, ARTICLE_DEFAULT, ARTICLE_IMAGE, 
  ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT, ARTICLE_TYPES)
from model.user import Group
from flask.views import View
from flask.ext.mongoengine.wtf import model_form, model_fields

from resource import ResourceHandler, ResourceHandler2, ResourceAccessStrategy, RacModelConverter
from raconteur import auth, db
from itertools import groupby
from datetime import datetime, timedelta
from wtforms.fields import FieldList, HiddenField
from werkzeug.datastructures import ImmutableMultiDict

world_app = Blueprint('world', __name__, template_folder='../templates/world')

world_strategy = ResourceAccessStrategy(World, 'worlds', 'slug')
class WorldHandler(ResourceHandler2):
  def myworlds(self, r):
    return self.list(r)
    
WorldHandler.register_urls(world_app, world_strategy)

# field_dict = model_fields(Article, exclude=['slug'])
# for k in field_dict:
#   print k, field_dict[k], "\n"
# for f in Article._fields.keys():
#   print f
artform = model_form(Article, exclude=['slug'], converter=RacModelConverter())

article_strategy = ResourceAccessStrategy(Article, 'articles', 'slug', parent_strategy=world_strategy, form_class = artform)
ResourceHandler2.register_urls(world_app, article_strategy)

article_relation_strategy = ResourceAccessStrategy(ArticleRelation, 'relations', None, parent_strategy=article_strategy)

ResourceHandler2.register_urls(world_app, article_relation_strategy)

# @world_app.route('/')
# def index():
#     worlds = World.objects()
#     return render_template('world/base.html', worlds=worlds)



@world_app.route('/image/<slug>')
def image(slug):
  imagearticle= Article.objects(slug=slug).first_or_404().imagearticle
  response = make_response(imagearticle.image.read())
  response.mimetype = imagearticle.mime_type
  return response

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
