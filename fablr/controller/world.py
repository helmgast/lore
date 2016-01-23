"""
    controller.world
    ~~~~~~~~~~~~~~~~

    This is the controller and Flask blueprint for game world features,
    it initializes URL routes based on the Resource module and specific
    ResourceRoutingStrategy for each world related model class. This module is then
    responsible for taking incoming URL requests, parse their parameters,
    perform operations on the Model classes and then return responses via
    associated template files.

    :copyright: (c) 2014 by Helmgast AB
"""

import os.path
from flask import request, redirect, url_for, render_template, Blueprint, flash, make_response, g, abort, current_app
from fablr.model.world import (Article, World, ArticleRelation, PersonData, PlaceData,
  EventData, FractionData, PublishStatus, Publisher)
from fablr.model.user import Group
from flask.views import View
from flask.ext.mongoengine.wtf import model_form, model_fields
from collections import OrderedDict
from gridfs.errors import FileExists
from fablr.controller.resource import (ResourceHandler, ResourceRoutingStrategy,
    ResourceAccessPolicy, RacModelConverter, ArticleBaseForm, RacBaseForm,
    render, make_list_args, make_get_args, make_edit_args, ResourceView,
    parse_args, tune_query, log_event)
from fablr.extensions import db, csrf
from itertools import groupby
from datetime import datetime, timedelta
from wtforms import Form
from wtforms import fields as f, validators as v, widgets
from werkzeug.datastructures import ImmutableMultiDict
from mongoengine.queryset import Q
from flask.ext.babel import lazy_gettext as _
from werkzeug.contrib.atom import AtomFeed
from flask.ext.classy import route

logger = current_app.logger if current_app else logging.getLogger(__name__)

world_app = Blueprint('world', __name__, template_folder='../templates/world')

# All articles have a publisher, some have world. If no world, it has the meta world, "meta". There is a default 1st publisher, called "system". So "system/meta/about"
# could be the about article in the meta-world (or namespace) of the system publisher. To reach a specific article, we need the full path.
#
# :publisher.tld/:world/:article --> ArticleHandler.get(pub, world, article). For uniqueness, an article full id is  :article_slug = 'helmgast/mundana/drunok'
# :publisher.tld/list -> ArticleHandler.list(pub, world=None) --> all articles in a publisher, regardless of world
# :publisher.tld/:world/:list --> ArticleHandler.list(pub, world) --> all articles given publisher and world
# :publisher.tld/worlds/list -> WorldHandler.list(pub) --> all articles in a publisher, regardless of world
# :publisher.tld/ --> PublisherHandler.index(pub)

# WorldHandler.register_urls(world_app, world_strategy)

def publish_filter(qr):
  if not g.user:
    return qr.filter(status=PublishStatus.published, created_date__lte=datetime.utcnow())
  elif g.user.admin:
    return qr
  else:
    return qr.filter(Q(status=PublishStatus.published, created_date__lte=datetime.utcnow()) | Q(creator=g.user))

class PublishersView(ResourceView):
    list_template = 'world/publisher_list.html'
    item_template = 'world/publisher_item.html'
    form_class = model_form(World, base_class=RacBaseForm, converter=RacModelConverter())
    access = ResourceAccessPolicy({
        'view':'user',
        '_default':'admin'
    })

    @render(html=list_template, json=None)
    def index(self):
        auth = self.access.auth_or_abort('list')
        publishers = Publisher.objects()
        return dict(publishers=publishers)

    @render(html=item_template, json=None)
    def get(self, id):
        publisher = Publisher.objects(slug=id).first_or_404()
        auth = self.access.auth_or_abort('view', publisher)
        return dict(publisher=publisher)

    def post(self):
        abort(501) # Not implemented

    def patch(self, id):
        abort(501) # Not implemented

    def delete(self, id):
        abort(501) # Not implemented

class WorldsView(ResourceView):
    route_base = '/'
    list_template = 'world/world_list.html'
    item_template = 'world/world_item.html'
    form_class = model_form(World, base_class=RacBaseForm, exclude=['slug'], converter=RacModelConverter())
    access = ResourceAccessPolicy()

    @route('/worlds/')
    @render(html=list_template, json=None)
    def index(self):
        response = parse_args(dict(worlds = World.objects(), action='list'), self.list_args) # sets response['args']
        response = self.access.auth_or_abort(response) # sets response['auth']
        response['worlds'] = publish_filter(response['worlds']).order_by('title') # set filter
        response = tune_query(response, 'worlds')  # sets filtering rules for list, response['pagination']
        return response

    @route('/<id>', defaults={'intent':''}, endpoint="WorldsView:get")
    @route('/<id>/<any(put,patch):intent>', endpoint="WorldsView:get")
    @route('/worlds/<any(post):intent>', defaults={'id':None}, endpoint="WorldsView:get")
    @render(html=item_template, json=None)
    def get(self, id, intent):
        world = World.objects(slug=id).first_or_404()
        if world.slug=='kult':
            g.lang = 'en'
        response = dict(world=world, intent=intent, action='view')
        response = self.access.auth_or_abort(response, instance=world) # sets response['auth']
        response = parse_args(response, self.get_args) # sets response['args']
        if intent in ['post', 'put', 'patch', 'delete']: # a form is intended
            response['world_form'] = self.form_class(obj=world, **response['args']['keys'])
            response['action_url'] = '' #url_for('world.WorldsView:get', **request.view_args)
            print response['action_url']
        theme_template = 'themes/%s-theme.html' % world.slug
        response['theme'] = current_app.jinja_env.get_or_select_template([theme_template, '_page.html'])

        return response

    def post(self):
        abort(501) # Not implemented

    @render(html=item_template, json=None)
    def patch(self, id):
        world = World.objects(slug=id).first_or_404()
        response = self.access.auth_or_abort(dict(world=world, action='edit'), instance=world)
        response = parse_args(response, self.edit_args) # sets response['args']
        form = self.form_class(request.form, obj=world)
        if not isinstance(form, RacBaseForm):
            raise ValueError("Edit op requires a form that supports populate_obj(obj, fields_to_populate)")
        if not form.validate():
            # return same page but with form errors?
            response['world_form'] = form
            return response
            # abort(400, response) # BadRequest
        form.populate_obj(world, request.form.keys()) # only populate selected keys
        world.save()
        log_event('patch', world)
        next = response['args']['next'] or url_for('world.WorldsView:get', id=world.slug)
        return redirect(next)

    def delete(self, id):
        abort(501) # Not implemented

class ArticlesView(ResourceView):
    route_base = '/<world>'
    list_template = 'world/article_list.html'
    item_template = 'world/article_item.html'
    form_class=model_form(Article,
        base_class=ArticleBaseForm,
        exclude=['slug'],
        converter=RacModelConverter())
    access = ResourceAccessPolicy()
    list_args = make_list_args(['title','type', 'creator', 'created_date'])
    get_args = make_get_args(['title', 'type', 'creator', 'created_date'])
    edit_args = make_edit_args()

    @route('/articles/')
    @render(html=list_template, json=None)
    def index(self, world):
        world = World.objects(slug=world).first_or_404()
        if world.slug=='kult':
            g.lang = 'en'
        articles = Article.objects(world=world)
        response = parse_args(dict(world=world, articles=articles, action='list'), self.list_args) # sets response['args']
        response = self.access.auth_or_abort(response) # sets response['auth']

        response['articles'] = publish_filter(response['articles']).order_by('-created_date') # set filter
        # print list(response['articles'])

        response = tune_query(response, 'articles')  # sets filtering rules for list, response['pagination']

        print type(response['articles'])
        theme_template = 'themes/%s-theme.html' % world.slug
        response['theme'] = current_app.jinja_env.get_or_select_template([theme_template, '_page.html'])
        return response

    # @route('/<world>/blog')
    @render(html='world/article_blog.html', json=None)
    def blog(self, world):
        # If decorated by @render, 'norender' means to skip rendering
        response = self.index(world, norender=True)
        # response['articles']._ordering # get ordering
        response['args']['view'] = 'list'
        response['articles'] = response['pagination'].iterable.filter(type='blogpost').order_by('-featured', '-created_date')
        response = tune_query(response, 'articles')  # sets filtering rules for list, response['pagination']
        return response

    # @route('/<world>/feed')
    # No renderer needed, it renders itself
    def feed(self, world):
        world = World.objects(slug=world).first_or_404()
        feed = AtomFeed(_('Recent Articles in ')+world.title,
          feed_url=request.url, url=request.url_root)
        articles = Article.objects(status=PublishStatus.published,
          created_date__lte=datetime.utcnow()).order_by('-created_date')[:10]
        for article in articles:
            feed.add(article.title, current_app.md._instance.convert(article.content),
               content_type='html',
               author=str(article.creator) if article.creator else 'System',
               url=url_for('world.ArticlesView:get', world=world.slug, id=article.slug, _external=True),
               updated=article.created_date,
               published=article.created_date)
        return feed.get_response()

    # articles/<intent>post
    # articles/<id>
    # articles/<id>/patch
    # articles/<id>/put
    # important that /post comes below /<id>
    @route('/<id>', defaults={'intent':''}, endpoint="ArticlesView:get")
    @route('/<id>/<any(put,patch):intent>', endpoint="ArticlesView:get")
    @route('/articles/<any(post):intent>', defaults={'id':None}, endpoint="ArticlesView:get")
    @render(html=item_template, json=None)
    def get(self, world, id, intent):
        world = World.objects(slug=world).first_or_404()
        if world.slug=='kult':
            g.lang = 'en'
        article = Article.objects(slug=id).first_or_404() if id else None
        response = dict(article=article, world=world, intent=intent, action='view')
        response = self.access.auth_or_abort(response, instance=article) # sets response['auth']
        response = parse_args(response, self.get_args) # sets response['args']
        if intent in ['post', 'put', 'patch', 'delete']: # a form is intended
            response['article_form'] = self.form_class(obj=article, world=world, **response['args']['keys'])
            response['action_url'] = ''#url_for('world.ArticlesView:%s' % intent,  method=intent.upper(), **{k:v for k,v in request.view_args.iteritems() if k!='intent'} )
        theme_template = 'themes/%s-theme.html' % world.slug if world.slug=='kult' else ''
        response['theme'] = current_app.jinja_env.get_or_select_template([theme_template, '_page.html'])
        print "--Reading------------------\n%s\n----------------------------" % article.content
        return response

    @route('/articles/', methods=['POST'])
    @render(html=item_template, json=None)
    def post(self, world):
        world = World.objects(slug=world).first_or_404()
        response = parse_args(dict(world=world, action='new'), self.edit_args) # sets response['args']
        article = Article()
        form = self.form_class(request.form, obj=article)
        if not form.validate():
            # return same page but with form errors?
            abort(400, form.errors) # BadRequest
        form.populate_obj(article)
        print "-Post-new----------------------\n%s\n----------------------------" % article.content
        article.save()
        log_event('post', article)
        next = response['args']['next'] or url_for('world.ArticlesView:get', id=article.slug, world=world.slug)
        return redirect(next)

    @render(html=item_template, json=None)
    def patch(self, world, id):
        world = World.objects(slug=world).first_or_404()
        article = Article.objects(slug=id).first_or_404()
        response = dict(article=article, world=world, action='edit')
        response = self.access.auth_or_abort(response, instance=article)
        response = parse_args(response, self.edit_args) # sets response['args']
        form = self.form_class(request.form, obj=article)
        if not isinstance(form, RacBaseForm):
            raise ValueError("Edit op requires a form that supports populate_obj(obj, fields_to_populate)")
        if not form.validate():
            # return same page but with form errors?
            abort(400, response) # BadRequest
        form.populate_obj(article, request.form.keys()) # only populate selected keys
        print "--Post-edit---------------\n%s\n----------------------------" % article.content
        article.save()
        log_event('patch', article)
        next = response['args']['next'] or url_for('world.ArticlesView:get', id=article.slug, world=world.slug)
        return redirect(next)

    @render(html=item_template, json=None)
    def delete(self, world, id):
        world = World.objects(slug=world).first_or_404()
        article = Article.objects(slug=id).first_or_404()
        response = dict(article=article, world=world, action='delete')
        response = self.access.auth_or_abort(response, instance=article)
        response = parse_args(response, self.edit_args) # sets response['args']
        next = response['args']['next'] or url_for('world.ArticlesView:index', world=world.slug)
        article.delete()
        log_event('delete', article)
        return redirect(next)

class ArticleRelationsView(ResourceView):
    route_base = '/<world>/<article>'
    list_template = 'world/articlerelation_list.html'
    item_template = 'world/articlerelation_item.html'
    form_class = model_form(World, base_class=RacBaseForm, converter=RacModelConverter())
    access = ResourceAccessPolicy()

    @route('/relations/')
    def index(self, world):
        abort(501) # Not implemented

@world_app.route('/')
@render(html='helmgast.html', json=None)
def homepage():
    world = World.objects(slug='helmgast').first_or_404()
    articles = Article.objects().filter(type='blogpost').order_by('-featured', '-created_date')
    response = ArticlesView.access.auth_or_abort(dict(world=world, articles=articles, action='list'))
    return response

PublishersView.register_with_access(world_app, 'publisher')
WorldsView.register_with_access(world_app, 'world')
ArticlesView.register_with_access(world_app, 'article')
ArticleRelationsView.register_with_access(world_app, 'articlerelations')


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
def dummygrouper(objects):
  return [{'grouper': None, 'list':objects}]

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

world_app.add_app_template_filter(dummygrouper)
world_app.add_app_template_filter(by_initials)
world_app.add_app_template_filter(by_articletype)
world_app.add_app_template_filter(by_time)
world_app.add_app_template_filter(rows)
