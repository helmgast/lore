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

from flask import request, redirect, url_for, Blueprint, g, abort, current_app, render_template, flash
from flask_babel import lazy_gettext as _
from flask_classy import route
from flask_mongoengine.wtf import model_form
from mongoengine import NotUniqueError, ValidationError
from mongoengine.queryset import Q
from werkzeug.contrib.atom import AtomFeed

from lore.api.resource import (ResourceAccessPolicy, ImprovedModelConverter, ArticleBaseForm, ImprovedBaseForm,
    ResourceView, filterable_fields_parser, prefillable_fields_parser,
                                ListResponse, ItemResponse, Authorization)
from lore.model.misc import EMPTY_ID, set_lang_options
from lore.model.world import (Article, World, PublishStatus, Publisher, WorldMeta, Shortcut)

logger = current_app.logger if current_app else logging.getLogger(__name__)

world_app = Blueprint('world', __name__)


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


# TODO doesn't catch the case where an article is published but it's world or Publisher is not.
# Useful filter generators below here
def filter_published():
    return Q(status=PublishStatus.published, created_date__lte=datetime.utcnow())


def filter_authorized():
    if not g.user:
        return Q(id=EMPTY_ID)
    return Q(editors__in=[g.user]) | Q(readers__in=[g.user])


def filter_authorized_by_world(world=None):
    if not g.user:
        return Q(id=EMPTY_ID)  # Empty
    elif not world:
        # Check all worlds
        return Q(world__in=World.objects(Q(editors__all=[g.user]) | Q(readers__all=[g.user])))
    elif g.user in world.editors or g.user in world.readers:
        # Save some time and only check given world
        return Q(world__in=[world])
    else:
        return Q(id=EMPTY_ID)


def filter_authorized_by_publisher(publisher=None):
    if not g.user:
        return Q(id=EMPTY_ID)
    if not publisher:
        # Check all publishers
        return Q(publisher__in=Publisher.objects(Q(editors__all=[g.user]) | Q(readers__all=[g.user])))
    elif g.user in publisher.editors or g.user in publisher.readers:
        # Save some time and only check given publisher
        return Q(publisher__in=[publisher])
    else:
        return Q(id=EMPTY_ID)


class PublisherAccessPolicy(ResourceAccessPolicy):
    def is_editor(self, op, user, res):
        if user in res.editors:
            return Authorization(True, _('Allowed access to "%(res)s" as editor', res=res), privileged=True)
        else:
            return Authorization(False, _('Not allowed access to "%(res)s" as not an editor', res=res))

    def is_reader(self, op, user, res):
        if user in res.readers:
            return Authorization(True, _('Allowed access to "%(res)s" as reader', res=res), privileged=True)
        else:
            return Authorization(False, _('Not allowed access to "%(res)s" as not a reader', res=res))

    def is_resource_public(self, op, res):
        return Authorization(True, _("Public resource")) if res.status == 'published' else \
            Authorization(False, _("Not a public resource"))

    def is_contribution_allowed(self, op, res):
        return Authorization(True, _("Publisher flagged as open for contribution")) if res.contribution else \
            Authorization(False, _("Publisher not open for contribution"))


class WorldAccessPolicy(PublisherAccessPolicy):
    def is_editor(self, op, user, res):
        if user in res.editors or (res.publisher and user in res.publisher.editors):
            return Authorization(True, _('Allowed access to %(op)s "%(res)s" as editor', op=op, res=res), privileged=True)
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not an editor', op=op, res=res))

    def is_reader(self, op, user, res):
        if user in res.readers or (res.publisher and user in res.publisher.readers):
            return Authorization(True, _('Allowed access to %(op)s "%(res)s" as reader', op=op, res=res), privileged=True)
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not a reader', op=op, res=res))

    def is_contribution_allowed(self, op, res):
        return Authorization(True, _("World flagged as open for contribution")) if res.contribution else \
            Authorization(False, _("World not open for contribution"))


class ArticleAccessPolicy(PublisherAccessPolicy):
    new_allowed = Authorization(True, _('Creating new resource is allowed'))

    def is_editor(self, op, user, res):
        if user in res.editors or \
                (res.publisher and user in res.publisher.editors) or \
                (res.world and user in res.world.editors):
            return Authorization(True, _('Allowed access to %(op)s "%(res)s" as editor', op=op, res=res),
                                 privileged=True)
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not an editor', op=op, res=res))

    def is_reader(self, op, user, res):
        if user in res.readers or \
                (res.publisher and user in res.publisher.readers) or \
                (res.world and user in res.world.readers):
            return Authorization(True, _('Allowed access to %(op)s "%(res)s" as reader', op=op, res=res),
                                 privileged=True)
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not a reader', op=op, res=res))


class PublishersView(ResourceView):
    access_policy = PublisherAccessPolicy()
    model = Publisher
    list_template = 'world/publisher_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'owner', 'created_date'])
    item_template = 'world/publisher_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'owner', 'created_date'])
    form_class = model_form(Publisher, base_class=ImprovedBaseForm, converter=ImprovedModelConverter())

    def index(self):
        r = ListResponse(PublishersView, [('publishers', Publisher.objects())])
        r.auth_or_abort(res=None)
        if not (g.user and g.user.admin):
            r.query = r.query.filter(
                filter_published() |
                filter_authorized())
        return r

    def get(self, id):
        if id == 'post':
            r = ItemResponse(PublishersView, [('publisher', None)], extra_args={'intent': 'post'})
            r.auth_or_abort(res=None)
        else:
            publisher = Publisher.objects(slug=id).first_or_404()
            r = ItemResponse(PublishersView, [('publisher', publisher)])
            r.auth_or_abort()
        return r

    def post(self):
        r = ItemResponse(PublishersView, [('publisher', None)], method='post')
        r.auth_or_abort(res=None)
        publisher = Publisher()
        if not r.validate():
            return r.error_response(status=400)
        r.form.populate_obj(publisher)
        try:
            r.commit(new_instance=publisher)
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.PublishersView:get', id=publisher.slug))

    def patch(self, id):
        publisher = Publisher.objects(slug=id).first_or_404()

        r = ItemResponse(PublishersView, [('publisher', publisher)], method='patch')
        r.auth_or_abort()
        if not r.validate():
            return r.error_response(status=400)

        r.form.populate_obj(publisher, list(request.form.keys()))  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.PublishersView:get', id=publisher.slug))

    def delete(self, id):
        abort(501)  # Not implemented


class WorldsView(ResourceView):
    subdomain = '<pub_host>'
    # route_base = '/'
    access_policy = WorldAccessPolicy()
    model = World
    list_template = 'world/world_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'publisher', 'creator', 'created_date'])
    item_template = 'world/world_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'publisher', 'creator', 'created_date'])
    form_class = model_form(World, base_class=ImprovedBaseForm, exclude=['slug'], converter=ImprovedModelConverter())
    # @route('/worlds/')

    def index(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)
        r = ListResponse(WorldsView, [('worlds', World.objects().order_by('title')), ('publisher', publisher)])

        r.auth_or_abort(res=publisher)

        if not (g.user and g.user.admin):
            r.query = r.query.filter(
                filter_published() |
                filter_authorized() |
                filter_authorized_by_publisher(publisher))
        r.prepare_query()
        r.set_theme('publisher', publisher.theme)
        return r

    def get(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()

        if id == 'post':
            set_lang_options(publisher)
            r = ItemResponse(WorldsView, [('world', None), ('publisher', publisher)], extra_args={'intent': 'post'})
            r.set_theme('world')  # Will pick from args if exist
            r.auth_or_abort(res=publisher)  # check auth scoped to publisher, as we want to create new
        else:
            world = World.objects(slug=id).first_or_404()
            if 'intent' not in request.args:
                # Redirect to home if we are just doing a get
                return redirect(url_for('world.ArticlesView:world_home', world_=world.slug))

            set_lang_options(world, publisher)
            r = ItemResponse(WorldsView, [('world', world), ('publisher', publisher)])
            r.auth_or_abort()
            r.set_theme('world', world.theme)
        r.set_theme('publisher', publisher.theme)
        return r

    def post(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        r = ItemResponse(WorldsView, [('world', None), ('publisher', publisher)], method='post')
        r.auth_or_abort(res=publisher)
        r.set_theme('publisher', publisher.theme)
        world = World()
        if not r.validate():
            return r.error_response(status=400)

        r.form.populate_obj(world)
        try:
            r.commit(new_instance=world)
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.WorldsView:get', pub_host=publisher.slug, id=world.slug))

    def patch(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = World.objects(slug=id).first_or_404()
        set_lang_options(world, publisher)

        r = ItemResponse(WorldsView, [('world', world), ('publisher', publisher)], method='patch')
        r.auth_or_abort()
        r.set_theme('publisher', publisher.theme)
        if not r.validate():
            return r.error_response(status=400)

        r.form.populate_obj(world, list(request.form.keys()))  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.WorldsView:get', pub_host=publisher.slug, id=world.slug))

    def delete(self, id):
        abort(501)  # Not implemented


def if_not_meta(doc):
    if isinstance(doc, WorldMeta):
        return None
    else:
        return doc


class ArticlesView(ResourceView):
    subdomain = '<pub_host>'
    route_base = '/<world_>'
    access_policy = ArticleAccessPolicy()
    model = Article
    list_template = 'world/article_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'type', 'creator', 'created_date', 'tags', 'status'])
    item_template = 'world/article_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'type', 'creator', 'created_date', 'theme', 'cloudinary'])
    form_class = model_form(Article,
                            base_class=ArticleBaseForm,
                            exclude=['slug', 'feature_image', 'featured'],
                            converter=ImprovedModelConverter())

    @route('/', route_base='/')
    def publisher_home(self):
        # Explicitly take pub_host as argument, not g variable
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = WorldMeta(publisher)
        articles = Article.objects(publisher=publisher).filter(type='blogpost').order_by('-sort_priority',
                                                                                         '-created_date')
        set_lang_options(publisher)
        r = ListResponse(ArticlesView, [('articles', articles), ('world', world), ('publisher', publisher)],
                         formats=['html'])
        r.auth_or_abort(res=publisher)
        r.template = 'world/publisher_home.html'
        if not (g.user and g.user.admin):
            r.query = r.query.filter(
                filter_published() |
                filter_authorized() |
                filter_authorized_by_publisher(publisher) |
                filter_authorized_by_world())
        r.worlds = publisher.worlds().filter(__raw__={'images': {'$gt': []}}).filter(filter_published())
        r.query = r.query.limit(8)
        r.prepare_query()
        r.set_theme('publisher', publisher.theme)
        return r

    @route('/<world_>/', route_base='/')
    def world_home(self, world_):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        if world_ == 'post':
            set_lang_options(publisher)
            r = ItemResponse(WorldsView, [('world', None), ('publisher', publisher)], extra_args={'intent': 'post'})
            r.auth_or_abort(res=publisher)  # check auth scoped to publisher, as we want to create new
        if world_ == 'meta':
            return redirect(url_for('world.ArticlesView:publisher_home', pub_host=publisher.slug))
        else:
            world = World.objects(slug=world_).first_or_404()
            set_lang_options(world, publisher)

            r = ItemResponse(WorldsView,
                             [('world', world), ('publisher', publisher)])
            r.auth_or_abort()
            if world.external_host:
                return redirect(world.external_host)
            r.set_theme('world', world.theme)
            r.articles = Article.objects(world=world).filter(
                filter_published() |
                filter_authorized() |
                filter_authorized_by_publisher(publisher) |
                filter_authorized_by_world(world))
        r.set_theme('publisher', publisher.theme)
        r.template = 'world/world_home.html'
        return r

    @route('/search', route_base='/')
    def search(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = WorldMeta(publisher)
        articles = Article.objects(publisher=publisher)
        set_lang_options(publisher)
        r = ListResponse(ArticlesView,
                         [('articles', articles), ('world', world), ('publisher', publisher)])
        r.auth_or_abort(res=publisher)
        if not (g.user and g.user.admin):
            r.query = r.query.filter(
                filter_published() |
                filter_authorized() |
                filter_authorized_by_publisher(publisher) |
                filter_authorized_by_world())
        r.prepare_query()
        r.set_theme('publisher', publisher.theme)
        r.template = 'world/article_search.html'
        return r

    @route('/articles/')  # Needed to give explicit route to index page, as route base shows world_item
    def index(self, world_):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        set_lang_options(world, publisher)

        if world_ == 'meta':
            articles = Article.objects(publisher=publisher).order_by('-created_date')  # All articles from publisher
        else:
            articles = Article.objects(world=world).order_by('-created_date')

        r = ListResponse(ArticlesView,
                         [('articles', articles), ('world', world), ('publisher', publisher)])
        r.auth_or_abort(res=(world if world_ != 'meta' else publisher))
        if not (g.user and g.user.admin):
            r.query = r.query.filter(
                filter_published() |
                filter_authorized() |
                filter_authorized_by_publisher(publisher) |
                filter_authorized_by_world(world))  # If world is meta will count as None

        r.prepare_query()
        r.set_theme('publisher', publisher.theme)
        r.set_theme('world', world.theme)
        return r

    def blog(self, world_):
        r = self.index(world_)
        r.args['per_page'] = 5
        r.args['view'] = 'list'
        r.query = r.query.filter(type='blogpost').order_by('-created_date')
        r.template = 'world/article_blog.html'
        r.prepare_query()
        return r

    def random(self, world_):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        # TODO ignores publisher for the moment
        articles = Article.objects(world=if_not_meta(world), status=PublishStatus.published,
                                   created_date__lte=datetime.utcnow())
        # Uses efficient MongoDB aggregate. Returns a dict, not a MongoEngine object
        sample = list(articles.aggregate({'$sample': {'size': 1}}))
        if sample:
            return redirect(url_for('world.ArticlesView:get', pub_host=publisher.slug, world_=world.slug,
                                    id=sample[0]['slug']))
        else:
            return redirect(url_for('world.ArticlesView:index', pub_host=publisher.slug, world_=world.slug))

    def feed(self, world_):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        query = filter_published()
        if world_ == 'meta':
            world = WorldMeta(publisher)
            query = Q(publisher=publisher) & query
        else:
            world = World.objects(slug=world_).first_or_404()
            query = Q(world=world) & query

        feed = AtomFeed(_('Recent Articles in ') + world.title,
                        feed_url=request.url, url=request.url_root)
        articles = Article.objects(query).order_by('-created_date')[:10]
        for article in articles:
            feed.add(article.title, current_app.md.convert(article.content),
                     content_type='html',
                     author=str(article.creator) if article.creator else 'System',
                     url=url_for('world.ArticlesView:get', world_=world.slug, id=article.slug, _external=True,
                                 _scheme=''),
                     updated=article.created_date,
                     published=article.created_date,
                     categories=[{'term': getattr(article.world or article.publisher, 'title', 'None')}])
        return feed.get_response()

    def get(self, world_, id):

        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)

        set_lang_options(world, publisher)

        # Special id post means we interpret this as intent=post (to allow simple routing to get)
        if id == 'post':
            r = ItemResponse(ArticlesView,
                             [('article', None), ('world', world), ('publisher', publisher)],
                             extra_args={'intent': 'post'})
            # check auth scoped to world or publisher, as we want to create new and use them as parent

            r.auth_or_abort(res=world if world_ != 'meta' else publisher)
            r.set_theme('article')  # Will pick from args if exist

        else:
            r = ItemResponse(ArticlesView,
                             [('article', Article.objects(slug=id).first_or_404()), ('world', world),
                              ('publisher', publisher)])
            r.auth_or_abort()
            r.set_theme('article', r.article.theme)

        r.set_theme('publisher', publisher.theme)
        r.set_theme('world', world.theme)

        return r

    def post(self, world_):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        set_lang_options(world, publisher)

        r = ItemResponse(ArticlesView,
                         [('article', None), ('world', world), ('publisher', publisher)],
                         method='post')
        # Check auth scoped to world or publisher, as we want to create new and use them as parent
        r.auth_or_abort(res=world if world_ != 'meta' else publisher)
        r.set_theme('publisher', publisher.theme)
        r.set_theme('world', world.theme)

        article = Article()
        if not r.validate():
            return r.error_response(status=400)

        r.form.populate_obj(article)
        r.set_theme('article', article.theme)  # Incase we need to return to user for validation error

        try:
            r.commit(new_instance=article)
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.ArticlesView:get', id=article.slug, pub_host=publisher.slug,
                                                  world_=world.slug, intent='patch'))

    def patch(self, world_, id):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        article = Article.objects(slug=id).first_or_404()
        set_lang_options(world, publisher)

        r = ItemResponse(ArticlesView,
                         [('article', article), ('world', world), ('publisher', publisher)],
                         method='patch')
        r.auth_or_abort()
        r.set_theme('publisher', publisher.theme)
        r.set_theme('world', world.theme)
        r.set_theme('article', r.article.theme)

        if not r.validate():
            return r.error_response(status=400)
        r.form.populate_obj(article, list(request.form.keys()))  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.ArticlesView:get', id=article.slug, pub_host=publisher.slug,
                                                  world_=world.slug, intent='patch'))

    def delete(self, world_, id):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        article = Article.objects(slug=id).first_or_404()
        set_lang_options(world, publisher)

        r = ItemResponse(ArticlesView,
                         [('article', article), ('world', world), ('publisher', publisher)],
                         method='delete')
        r.auth_or_abort()
        r.set_theme('publisher', publisher.theme)
        r.set_theme('world', world.theme)
        r.set_theme('article', r.article.theme)

        r.commit()
        return redirect(
            r.args['next'] or url_for('world.ArticlesView:index', pub_host=publisher.slug, world_=world.slug))


# class ArticleRelationsView(ResourceView):
#     subdomain = '<pub_host>'
#     route_base = '/<world_>/<article>'
#     list_template = 'world/articlerelation_list.html'
#     item_template = 'world/articlerelation_item.html'
#     form_class = model_form(World, base_class=ImprovedBaseForm, converter=ImprovedModelConverter())
#     access_policy = ResourceAccessPolicy()
#
#     @route('/relations/')
#     def index(self, world_):
#         abort(501)  # Not implemented

@world_app.route('/+<code>', subdomain=current_app.default_host)
def shorturl(code):
    shortcut = Shortcut.objects(slug=code.lower()).first()
    url = ''
    if shortcut:
        if shortcut.article:
            url = url_for('world.ArticlesView:get',
                pub_host=shortcut.article.publisher.slug,
                world_=shortcut.article.world.slug,
                id=shortcut.article.slug)
        elif shortcut.url:
            url = shortcut.url
        if url:
            return redirect(url)
    abort(404, description=_("This code has not yet been created."))


@world_app.route('/', subdomain=current_app.default_host)
def homepage():
    publishers = Publisher.objects()
    return render_template('homepage.html', publishers=publishers)


@world_app.route('/styleguide')
def styleguide():
    # publishers = Publisher.objects()
    flash(_('This page is a rendered style guide and example of how to write an article'), 'info')
    return render_template('styleguide.html', root_template='_root.html')


PublishersView.register_with_access(world_app, 'publisher')
WorldsView.register_with_access(world_app, 'world')
ArticlesView.register_with_access(world_app, 'article')


# ArticleRelationsView.register_with_access(world_app, 'articlerelations')

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


world_app.add_app_template_filter(dummygrouper)
world_app.add_app_template_filter(by_initials)
world_app.add_app_template_filter(by_articletype)
world_app.add_app_template_filter(rows)
