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
import logging
from datetime import datetime
from itertools import groupby

from flask import request, redirect, url_for, Blueprint, g, abort, current_app
from flask.ext.babel import lazy_gettext as _
from flask.ext.classy import route
from flask.ext.mongoengine.wtf import model_form
from mongoengine.queryset import Q
from mongoengine import NotUniqueError
from werkzeug.contrib.atom import AtomFeed

from fablr.controller.resource import (ResourceAccessPolicy, RacModelConverter, ArticleBaseForm, RacBaseForm,
                                       ResourceView, filterable_fields_parser, prefillable_fields_parser,
                                       ListResponse, ItemResponse)
from fablr.model.world import (Article, World, PublishStatus, Publisher)

logger = current_app.logger if current_app else logging.getLogger(__name__)

world_app = Blueprint('world', __name__, template_folder='../templates/world')


# All articles have a publisher, some have world. If no world, it has the meta world, "meta". There is a default 1st
# publisher, called "system". So "system/meta/about"
# could be the about article in the meta-world (or namespace) of the system publisher. To reach a specific article,
# we need the full path.
#
# :publisher.tld/:world/:article --> ArticleHandler.get(pub, world, article). For uniqueness, an article full id is
# :article_slug = 'helmgast/mundana/drunok'
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
    access_policy = ResourceAccessPolicy({
        'view': 'user',
        '_default': 'admin'
    })
    model = Publisher
    list_template = 'world/publisher_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'owner', 'created_date'])
    item_template = 'world/publisher_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'owner', 'created_date'])
    form_class = model_form(Publisher, base_class=RacBaseForm, exclude=['slug'], converter=RacModelConverter())

    def index(self):
        r = ListResponse(PublishersView, [('publishers', Publisher.objects())])
        r.auth_or_abort()
        return r

    def get(self, id):
        publisher = Publisher.objects(slug=id).first_or_404()
        r = ItemResponse(PublishersView, [('publisher', publisher)])
        r.auth_or_abort()
        return r

    def post(self):
        abort(501)  # Not implemented

    def patch(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


class WorldsView(ResourceView):
    route_base = '/'
    access_policy = ResourceAccessPolicy({
        'view': 'public',
        'list': 'public',
        '_default': 'admin'
    })
    model = World
    list_template = 'world/world_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'publisher', 'creator', 'created_date'])
    item_template = 'world/world_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'publisher', 'creator', 'created_date'])
    form_class = model_form(World, base_class=RacBaseForm, exclude=['slug'], converter=RacModelConverter())

    @route('/worlds/')
    def index(self):
        r = ListResponse(WorldsView, [('worlds', World.objects())])
        r.auth_or_abort()
        r.worlds = publish_filter(r.worlds).order_by('title')
        r.prepare_query()
        return r

    def get(self, id):
        if id == 'post':
            r = ItemResponse(WorldsView, [('world', None)], extra_args={'intent': 'post'})
        else:
            r = ItemResponse(WorldsView, [('world', World.objects(slug=id).first_or_404())])
            if r.world.language:
                g.lang = r.world.language
        r.auth_or_abort()
        r.set_theme('themes/%s-theme.html' % id)  # id == world.slug
        return r

    def post(self):
        r = ItemResponse(WorldsView, [('world', None)], method='post')
        r.auth_or_abort()
        world = World()
        if not r.validate():
            return r, 400
        r.form.populate_obj(world)
        try:
            r.commit(new_instance=world)
        except NotUniqueError:
            r.form.title.errors.append('ID %s already in use')
            return r, 400
        return redirect(r.next)

    def patch(self, id):
        world = World.objects(slug=id).first_or_404()
        r = ItemResponse(WorldsView, [('world', world)], method='patch')
        if not isinstance(r.form, RacBaseForm):
            raise ValueError("Edit op requires a form that supports populate_obj(obj, fields_to_populate)")
        if not r.validate():
            # return same page but with form errors?
            return r, 400  # BadRequest
        r.form.populate_obj(world, request.form.keys())  # only populate selected keys
        r.commit()
        return redirect(r.next)

    def delete(self, id):
        abort(501)  # Not implemented


class ArticlesView(ResourceView):
    route_base = '/<world>'
    access_policy = ResourceAccessPolicy()
    model = Article
    list_template = 'world/article_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'type', 'creator', 'created_date'])
    item_template = 'world/article_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'type', 'creator', 'created_date'])
    form_class = model_form(Article,
                            base_class=ArticleBaseForm,
                            exclude=['slug'],
                            converter=RacModelConverter())

    @route('/articles/')  # Needed to give explicit route to index page, as route base shows world_item
    def index(self, world):
        world = World.objects(slug=world).first_or_404()
        if world.language:
            g.lang = world.language
        articles = Article.objects(world=world)
        r = ListResponse(ArticlesView,
                         [('articles', articles), ('world', world)])
        r.auth_or_abort()
        r.query = publish_filter(r.query).order_by('-created_date')
        r.prepare_query()
        r.set_theme('themes/%s-theme.html' % world.slug)
        return r

    def blog(self, world):
        r = self.index(world)
        r.args['view'] = 'list'
        r.articles = r.pagination.iterable.filter(type='blogpost').order_by('-featured', '-created_date')
        r.template = 'world/article_blog.html'
        r.prepare_query()
        return r

    def feed(self, world):
        world = World.objects(slug=world).first_or_404()
        feed = AtomFeed(_('Recent Articles in ') + world.title,
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

    def get(self, world, id):
        world = World.objects(slug=world).first_or_404()
        if world.language:
            g.lang = world.language
        # Special id post means we interpret this as intent=post (to allow simple routing to get)
        if id == 'post':
            r = ItemResponse(ArticlesView,
                             [('article', None), ('world', world)],
                             extra_args={'intent': 'post'})
        else:
            r = ItemResponse(ArticlesView,
                             [('article', Article.objects(slug=id).first_or_404()), ('world', world)])
        r.auth_or_abort()
        r.set_theme('themes/%s-theme.html' % world.slug)
        return r

    def post(self, world):
        world = World.objects(slug=world).first_or_404()
        if world.language:
            g.lang = world.language
        r = ItemResponse(ArticlesView,
                         [('article', None), ('world', world)],
                         method='post')
        r.auth_or_abort()
        article = Article()
        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(article)
        try:
            r.commit(new_instance=article)
        except NotUniqueError:
            r.form.title.errors.append('ID %s already in use')
            return r, 400  # Respond with same page, including errors highlighted
        return redirect(r.next)

    def patch(self, world, id):
        world = World.objects(slug=world).first_or_404()
        if world.language:
            g.lang = world.language
        article = Article.objects(slug=id).first_or_404()
        r = ItemResponse(ArticlesView,
                         [('article', article), ('world', world)],
                         method='patch')
        r.auth_or_abort()

        if not isinstance(r.form, RacBaseForm):
            raise ValueError("Edit op requires a form that supports populate_obj(obj, fields_to_populate)")
        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(article, request.form.keys())  # only populate selected keys
        r.commit()
        return redirect(r.next)

    def delete(self, world, id):
        world = World.objects(slug=world).first_or_404()
        if world.language:
            g.lang = world.language
        article = Article.objects(slug=id).first_or_404()
        r = ItemResponse(ArticlesView,
                         [('article', article), ('world', world)],
                         method='delete')
        r.auth_or_abort()
        r.commit()
        return redirect(r.next)


class ArticleRelationsView(ResourceView):
    route_base = '/<world>/<article>'
    list_template = 'world/articlerelation_list.html'
    item_template = 'world/articlerelation_item.html'
    form_class = model_form(World, base_class=RacBaseForm, converter=RacModelConverter())
    access_policy = ResourceAccessPolicy()

    @route('/relations/')
    def index(self, world):
        abort(501)  # Not implemented


@world_app.route('/')
def homepage():
    world = World.objects(slug='helmgast').first_or_404()
    articles = Article.objects().filter(type='blogpost').order_by('-featured', '-created_date')
    r = ListResponse(ArticlesView, [('articles', articles), ('world', world)], formats=['html'])
    r.template = 'helmgast.html'
    r.auth_or_abort()
    r.prepare_query()
    return r.render()


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
    return [{'grouper': None, 'list': objects}]


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
