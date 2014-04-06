"""
    controller.world
    ~~~~~~~~~~~~~~~~

    This is the controller and Flask blueprint for game world features,
    it initializes URL routes based on the Resource module and specific
    ResourceAccessStrategy for each world related model class. This module is then
    responsible for taking incoming URL requests, parse their parameters,
    perform operations on the Model classes and then return responses via 
    associated template files.

    :copyright: (c) 2014 by Raconteur
"""

from flask import request, redirect, url_for, render_template, Blueprint, flash, make_response, g, abort, current_app
from model.world import (Article, World, ArticleRelation, PersonData, PlaceData, 
  EventData, FractionData, PUBLISH_STATUS_PUBLISHED)
from model.user import Group
from flask.views import View
from flask.ext.mongoengine.wtf import model_form, model_fields
from collections import OrderedDict
from gridfs.errors import FileExists
from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter, ArticleBaseForm
from extensions import db, csrf
from itertools import groupby
from datetime import datetime, timedelta
from wtforms.fields import FieldList, HiddenField
from werkzeug.datastructures import ImmutableMultiDict
from mongoengine.queryset import Q
from flask.ext.babel import lazy_gettext as _

logger = current_app.logger if current_app else logging.getLogger(__name__)

world_app = Blueprint('world', __name__, template_folder='../templates/world')

world_strategy = ResourceAccessStrategy(World, 'worlds', 'slug', short_url=True)

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

WorldHandler.register_urls(world_app, world_strategy)


def publish_filter(qr):
  if not g.user:
    return qr.filter(status=PUBLISH_STATUS_PUBLISHED, created_date__lte=datetime.utcnow())
  elif g.user.admin:
    return qr
  else:
    logger.debug("Filtering to %s" % qr.filter(Q(status=PUBLISH_STATUS_PUBLISHED, created_date__lte=datetime.utcnow()) | Q(creator=g.user)))
    return qr.filter(Q(status=PUBLISH_STATUS_PUBLISHED, created_date__lte=datetime.utcnow()) | Q(creator=g.user))


class ArticleHandler(ResourceHandler):
  def blog(self, r):
    r['op'] = "list"
    r = self.list(r)
    r['template'] = 'world/article_blog.html'
    if r['pagination']:
      r['list'] = r['pagination'].iterable.filter(type='blogpost').order_by('-created_date')
    else:
      r['list'] = r['list'].filter(type='blogpost').order_by('-created_date')

    r['articles'] = r['list']
    return r

article_strategy = ResourceAccessStrategy(Article, 'articles', 'slug', parent_strategy=world_strategy, short_url=True,
                                          list_filters=publish_filter,
                                          form_class=model_form(Article, base_class=ArticleBaseForm, exclude=['slug'], converter=RacModelConverter()))
ArticleHandler.register_urls(world_app, article_strategy)

article_relation_strategy = ResourceAccessStrategy(ArticleRelation, 'relations', None, parent_strategy=article_strategy)

ResourceHandler.register_urls(world_app, article_relation_strategy)


@world_app.route('/')
def index():
    worlds = World.objects()
    return render_template('world/world_list.html', worlds=worlds)


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
