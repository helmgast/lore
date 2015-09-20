"""
    controller.world
    ~~~~~~~~~~~~~~~~

    This is the controller and Flask blueprint for game world features,
    it initializes URL routes based on the Resource module and specific
    ResourceRoutingStrategy for each world related model class. This module is then
    responsible for taking incoming URL requests, parse their parameters,
    perform operations on the Model classes and then return responses via 
    associated template files.

    :copyright: (c) 2014 by Raconteur
"""

from flask import request, redirect, url_for, render_template, Blueprint, flash, make_response, g, abort, current_app
from fablr.model.world import (Article, World, ArticleRelation, PersonData, PlaceData, 
  EventData, FractionData, PublishStatus)
from fablr.model.user import Group
from flask.views import View
from flask.ext.mongoengine.wtf import model_form, model_fields
from collections import OrderedDict
from gridfs.errors import FileExists
from fablr.controller.resource import ResourceHandler, ResourceRoutingStrategy, ResourceAccessPolicy, RacModelConverter, ArticleBaseForm
from fablr.extensions import db, csrf
from itertools import groupby
from datetime import datetime, timedelta
from wtforms.fields import FieldList, HiddenField
from werkzeug.datastructures import ImmutableMultiDict
from mongoengine.queryset import Q
from flask.ext.babel import lazy_gettext as _
from werkzeug.contrib.atom import AtomFeed

logger = current_app.logger if current_app else logging.getLogger(__name__)

world_app = Blueprint('world', __name__, template_folder='../templates/world')

world_strategy = ResourceRoutingStrategy(World, 'worlds', 'slug', short_url=True)

class WorldHandler(ResourceHandler):
  def myworlds(self, r):
    if g.user:
      # Worlds which this user has created articles for
      # TODO probably not efficient if many articles!
      arts = Article.objects(creator=g.user).only("world").select_related()
      worlds = [a.world for a in arts]
      r['template'] = self.strategy.list_template()
      r[self.strategy.plural_name] = worlds
      return r
    else:
      return self.list(r)

WorldHandler.register_urls(world_app, world_strategy, sub=True)

def publish_filter(qr):
  if not g.user:
    return qr.filter(status=PublishStatus.published, created_date__lte=datetime.utcnow())
  elif g.user.admin:
    return qr
  else:
    return qr.filter(Q(status=PublishStatus.published, created_date__lte=datetime.utcnow()) | Q(creator=g.user))


class ArticleHandler(ResourceHandler):
  def blog(self, r):
    r['op'] = 'list'
    r = self.list(r)
    r['template'] = 'world/article_blog.html'
    if r['pagination']:
      r['list'] = r['pagination'].iterable.filter(type='blogpost').order_by('-featured', '-created_date')
    else:
      r['list'] = r['list'].filter(type='blogpost').order_by('-featured', '-created_date')

    r['articles'] = r['list']
    return r

  def feed(self, r):
    world = r['parents']['world']
    feed = AtomFeed(_('Recent Articles in ')+world.title,
      feed_url=request.url, url=request.url_root)
    articles = Article.objects(status=PublishStatus.published, 
      created_date__lte=datetime.utcnow()).order_by('-created_date')[:10]
    for article in articles:
        # print current_app.md._instance.convert(article.content), type(current_app.md._instance.convert(article.content))
        feed.add(article.title, current_app.md._instance.convert(article.content),
           content_type='html',
           author=str(article.creator) if article.creator else 'System',
           url=url_for('world.article_view', world=world.slug, article=article.slug, _external=True),
           updated=article.created_date,
           published=article.created_date)
    r['response'] = feed.get_response()
    return r

article_strategy = ResourceRoutingStrategy(Article, 'articles', 'slug', 
  parent_strategy=world_strategy, 
  short_url=True,
  list_filters=publish_filter,
  form_class=model_form(Article, 
  base_class=ArticleBaseForm, 
  exclude=['slug'], 
  converter=RacModelConverter()))

ArticleHandler.register_urls(world_app, article_strategy)

# @current_app.context_processor
# def inject_access():
#     print _app_ctx_stack.top
#     return dict(article_access=article_strategy.access)

article_relation_strategy = ResourceRoutingStrategy(ArticleRelation, 'relations', 
  None, parent_strategy=article_strategy)

ResourceHandler.register_urls(world_app, article_relation_strategy)

# Not needed, now that World has same root as main app
# @world_app.route('/hej')
# def index():
#     worlds = World.objects()
#     return render_template('world/world_list.html', worlds=worlds)

def rows(objects, char_per_row=40, min_rows=10):
  found = 0
  if objects and isinstance(objects, str):
    start, end = 0, min(char_per_row, len(objects))
    while start < len(objects):
      i = objects.find('\n', start, end)
      found += 1
      logger.info("Reading char %i-%i, got %i, found %i", start, end - 1, i, found)
      if i == -1:
        start = end
        end += char_per_row
      else:
        start = i + 1
        end = start + char_per_row
  return max(found, min_rows)


# Template filter, will group a list by their initial title letter
def by_initials(objects):
  groups = []
  for s, t in groupby(sorted(objects, key=lambda x: x.title.upper()), lambda y: y.title[0:1].upper()):
    groups.append({'grouper': s, 'list': list(t)})
  return sorted(groups, key=lambda x: x['grouper'])


# Template filter, will group a list by their article type_name
def by_articletype(objects):
  groups = []
  for s, t in groupby(sorted(objects, key=lambda x: x.type), lambda y: y.type):
    groups.append({'grouper': s, 'list': sorted(list(t), key=lambda x: x.title)})
  return sorted(groups, key=lambda x: x['grouper'])


def prettydate(d):
  diff = datetime.utcnow() - d
  if diff.days < 1:
      return _('Today')
  elif diff.days < 7:
      return _('Last week')
  elif diff.days < 31:
      return _('Last month')
  elif diff.days < 365:
      return _('Last year')
  else:
        return _('Older')


# Template filter, will group a list by creation date, as measure in delta from now
def by_time(objects):
  groups = []
  for s, t in groupby(sorted(objects, key=lambda x: x.created_date), lambda y: prettydate(y.created_date)):
    groups.append({'grouper': s, 'list': sorted(list(t), key=lambda x: x.title)})
  return sorted(groups, key=lambda x: x['list'][0].created_date, reverse=True)

world_app.add_app_template_filter(by_initials)
world_app.add_app_template_filter(by_articletype)
world_app.add_app_template_filter(by_time)
world_app.add_app_template_filter(rows)
