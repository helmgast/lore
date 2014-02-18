from flask import request, redirect, url_for, render_template, Blueprint, flash, make_response, g
from model.world import (Article, World, ArticleRelation, PersonArticle, PlaceArticle, 
  EventArticle, ImageArticle, FractionArticle, ARTICLE_DEFAULT, ARTICLE_IMAGE, 
  ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT, ARTICLE_BLOG, ARTICLE_TYPES)
from model.user import Group
from flask.views import View
from flask.ext.mongoengine.wtf import model_form, model_fields

from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter, ArticleBaseForm
from raconteur import auth, db
from itertools import groupby
from datetime import datetime, timedelta
from wtforms.fields import FieldList, HiddenField
from werkzeug.datastructures import ImmutableMultiDict

world_app = Blueprint('world', __name__, template_folder='../templates/world')

world_strategy = ResourceAccessStrategy(World, 'worlds', 'slug', short_url=True)

class WorldHandler(ResourceHandler):
  def myworlds(self, r):
    # Worlds which this user has created articles for
    # TODO probably not efficient if many articles!
    arts = Article.objects(creator=g.user).only("world").select_related()
    worlds = [a.world for a in arts]
    r['template'] = self.strategy.list_template()
    r[self.strategy.plural_name] = worlds
    return r    

WorldHandler.register_urls(world_app, world_strategy)

class ArticleHandler(ResourceHandler):
  def blog(self, r):
    r = self.list(r)
    r['template'] = 'world/article_blog.html'
    r['list'] = r['list'].filter(type=ARTICLE_BLOG).order_by('-created_date')
    r['articles'] = r['list']
    return r

article_strategy = ResourceAccessStrategy(Article, 'articles', 'slug', parent_strategy=world_strategy, 
  form_class = model_form(Article, base_class=ArticleBaseForm, exclude=['slug'], converter=RacModelConverter()), short_url=True)
ArticleHandler.register_urls(world_app, article_strategy)

article_relation_strategy = ResourceAccessStrategy(ArticleRelation, 'relations', None, parent_strategy=article_strategy)

ResourceHandler.register_urls(world_app, article_relation_strategy)

@world_app.route('/')
def index():
    worlds = World.objects()
    return render_template('world/world_list.html', worlds=worlds)

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
