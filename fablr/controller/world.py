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
import random
import re
from datetime import datetime
from itertools import groupby

from flask import request, redirect, url_for, Blueprint, g, abort, current_app, render_template, flash
from flask_babel import lazy_gettext as _
from flask_classy import route
from flask_mongoengine.wtf import model_form
from jinja2 import TemplateNotFound
from mongoengine.queryset import Q
from mongoengine import NotUniqueError, ValidationError
from werkzeug.contrib.atom import AtomFeed

from fablr.controller.resource import (ResourceAccessPolicy, RacModelConverter, ArticleBaseForm, RacBaseForm,
                                       ResourceView, filterable_fields_parser, prefillable_fields_parser,
                                       ListResponse, ItemResponse, Authorization)
from fablr.model.world import (Article, World, PublishStatus, Publisher, WorldMeta)

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
        '_default': 'admin'
    })
    model = Publisher
    list_template = 'world/publisher_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'owner', 'created_date'])
    item_template = 'world/publisher_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'owner', 'created_date'])
    form_class = model_form(Publisher, base_class=RacBaseForm, converter=RacModelConverter())

    def index(self):
        r = ListResponse(PublishersView, [('publishers', Publisher.objects())])
        r.auth_or_abort()
        return r

    def get(self, id):

        if id == 'post':
            r = ItemResponse(PublishersView, [('publisher', None)], extra_args={'intent': 'post'})
        else:
            publisher = Publisher.objects(slug=id).first_or_404()
            r = ItemResponse(PublishersView, [('publisher', publisher)])
        r.auth_or_abort()
        return r

    def post(self):
        r = ItemResponse(PublishersView, [('publisher', None)], method='post')
        r.auth_or_abort()
        publisher = Publisher()
        if not r.validate():
            flash(_("Error in form"), 'danger')
            return r, 400
        r.form.populate_obj(publisher)
        try:
            r.commit(new_instance=publisher)
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.PublishersView:get', id=publisher.slug))

    def patch(self, id):
        publisher = Publisher.objects(slug=id).first_or_404()

        r = ItemResponse(PublishersView, [('publisher', publisher)], method='patch')
        if not r.validate():
            # return same page but with form errors?
            flash(_("Error in form"), 'danger')
            return r, 400  # BadRequest
        r.form.populate_obj(publisher, request.form.keys())  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.PublishersView:get', id=publisher.slug))

    def delete(self, id):
        abort(501)  # Not implemented


domain_slug = re.compile(r'(www.)?([^.]+)')


def set_theme(response, theme_type, slug):
    if response and theme_type and slug:
        slug = domain_slug.search(slug).group(2)  # www.domain.tld --> domain
        try:
            setattr(response, '%s_theme' % theme_type,
                    current_app.jinja_env.get_template('themes/%s_%s.html' % (theme_type, slug)))
            # print "Using theme %s" % getattr(response, '%s_theme' % theme_type)
        except TemplateNotFound:
            logger.warning("Not finding theme %s_%s.html" % (theme_type, slug))


class WorldAccessPolicy(ResourceAccessPolicy):
    def is_editor(self, op, instance):
        if instance:
            if g.user in instance.editors:
                return Authorization(True, _("Allowed access to %(instance)s as editor", instance=instance),
                                     privileged=True)
            else:
                return Authorization(False, _("Not allowed access to %(instance)s as not an editor"))
        else:
            return Authorization(False, _("No instance to test for access on"))

    def is_owner(self, op, instance):
        if instance:
            if g.user == instance.creator:
                return Authorization(True, _("Allowed access to %(instance)s as creator", instance=instance),
                                     privileged=True)
            else:
                return Authorization(False, _("Not allowed access to %(instance)s as not an creator"))
        else:
            return Authorization(False, _("No instance to test for access on"))

    def get_access_level(self, op, instance):
        """Normally viewing a resource is public, unless status is private, draft or archived"""
        if instance:
            if op == 'view' and instance.status in (PublishStatus.private, PublishStatus.archived, PublishStatus.draft):
                return 'reader'
        return None  # means we will default to access level set in the policy


class WorldsView(ResourceView):
    subdomain = '<publisher_>'
    route_base = '/'
    access_policy = WorldAccessPolicy({
        'view': 'public',
        'list': 'public',
        'edit': 'editor',
        'new': 'editor',  # refers to editor of parent world/publisher passed to authorize() as instance
        '_default': 'admin'
    })
    model = World
    list_template = 'world/world_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'publisher', 'creator', 'created_date'])
    item_template = 'world/world_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'publisher', 'creator', 'created_date'])
    form_class = model_form(World, base_class=RacBaseForm, exclude=['slug'], converter=RacModelConverter(),
                            field_args={'readers': {'allow_blank': True}})

    @route('/')
    def publisher_home(self, publisher_):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = WorldMeta(publisher)
        articles = Article.objects(publisher=publisher).filter(type='blogpost').order_by('-featured', '-created_date')
        lang_options = world.languages or publisher.languages
        if lang_options:
            g.available_locales = lang_options
        r = ListResponse(ArticlesView, [('articles', articles), ('world', world), ('publisher', publisher)],
                         formats=['html'])
        r.template = 'world/home.html'
        r.auth_or_abort()
        r.prepare_query()
        set_theme(r, 'publisher', publisher.slug)
        return r

    @route('/worlds/')
    def index(self, publisher_):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        if publisher.languages:
            g.available_locales = publisher.languages
        r = ListResponse(WorldsView, [('worlds', World.objects()), ('publisher', publisher)])
        r.auth_or_abort()
        r.worlds = publish_filter(r.worlds).order_by('title')
        r.prepare_query()
        set_theme(r, 'publisher', publisher.slug)
        return r

    # # Lists all blogposts under a publisher, not world...
    # def blog(self, publisher):
    #     publisher = Publisher.objects(slug=publisher).first_or_404()
    #     articles = Article.objects(publisher=publisher, type='blogpost')
    #     if publisher.languages:
    #         g.available_locales = publisher.languages
    #     r = ListResponse(ArticlesView,
    #                      [('articles', articles), ('publisher', publisher)])
    #     r.auth_or_abort()
    #     r.template = ArticlesView.list_template
    #     r.query = publish_filter(r.query).order_by('-created_date')
    #     r.prepare_query()
    #     set_theme(r, 'publisher', publisher)
    #     return r

    def get(self, publisher_, id):
        return redirect(url_for('world.ArticlesView:world_home', publisher_=publisher_, world_=id))
        # publisher = Publisher.objects(slug=publisher_).first_or_404()
        # if publisher.languages:
        #     g.available_locales = publisher.languages
        # if id == 'post':
        #     r = ItemResponse(WorldsView, [('world', None), ('publisher', publisher)], extra_args={'intent': 'post'})
        #     r.auth_or_abort(instance=publisher)  # check auth scoped to publisher, as we want to create new
        # else:
        #     r = ItemResponse(WorldsView, [('world', World.objects(slug=id).first_or_404()), ('publisher', publisher)])
        #     r.auth_or_abort()
        #     set_theme(r, 'world', r.world.slug)
        # set_theme(r, 'publisher', publisher.slug)
        # return r

    def post(self, publisher_):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        if publisher.languages:
            g.available_locales = publisher.languages
        r = ItemResponse(WorldsView, [('world', None), ('publisher', publisher)], method='post')
        r.auth_or_abort()
        set_theme(r, 'publisher', publisher.slug)
        world = World()
        if not r.validate():
            flash(_("Error in form"), 'danger')
            return r, 400
        r.form.populate_obj(world)
        try:
            r.commit(new_instance=world)
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.WorldsView:get', publisher_=publisher.slug, id=world.slug))

    def patch(self, publisher_, id):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = World.objects(slug=id).first_or_404()
        lang_options = world.languages or publisher.languages
        if lang_options:
            g.available_locales = lang_options
        r = ItemResponse(WorldsView, [('world', world), ('publisher', publisher)], method='patch')
        set_theme(r, 'publisher', publisher.slug)
        if not r.validate():
            # return same page but with form errors?
            flash(_("Error in form"), 'danger')
            return r, 400  # BadRequest
        r.form.populate_obj(world, request.form.keys())  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.WorldsView:get', publisher_=publisher.slug, id=world.slug))

    def delete(self, publisher_, id):
        abort(501)  # Not implemented


def safeget(object, attr):
    if not object:
        if attr == 'slug':
            return 'meta'
        else:
            return None
    else:
        return getattr(object, attr, None)


def if_not_meta(doc):
    if isinstance(doc, WorldMeta):
        return None
    else:
        return doc


class ArticlesView(ResourceView):
    subdomain = '<publisher_>'
    route_base = '/<world_>'
    access_policy = WorldAccessPolicy({
        'view': 'public',
        'list': 'public',
        'edit': 'editor',
        'new': 'editor',  # refers to editor of parent world/publisher passed to authorize() as instance
        '_default': 'admin'
    })
    model = Article
    list_template = 'world/article_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'type', 'creator', 'created_date'])
    item_template = 'world/article_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'type', 'creator', 'created_date'])
    form_class = model_form(Article,
                            base_class=ArticleBaseForm,
                            exclude=['slug', 'feature_image'],
                            converter=RacModelConverter())

    @route('/')
    def world_home(self, publisher_, world_):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        if publisher.languages:
            g.available_locales = publisher.languages
        if world_ == 'post':
            r = ItemResponse(WorldsView, [('world', None), ('publisher', publisher)], extra_args={'intent': 'post'})
            r.auth_or_abort(instance=publisher)  # check auth scoped to publisher, as we want to create new
        else:
            r = ItemResponse(WorldsView,
                             [('world', World.objects(slug=world_).first_or_404()), ('publisher', publisher)])
            r.auth_or_abort()
            set_theme(r, 'world', r.world.slug)
        set_theme(r, 'publisher', publisher.slug)
        return r

    @route('/articles/')  # Needed to give explicit route to index page, as route base shows world_item
    def index(self, publisher_, world_):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        lang_options = world.languages or publisher.languages
        if lang_options:
            g.available_locales = lang_options
        articles = Article.objects(world=if_not_meta(world))
        r = ListResponse(ArticlesView,
                         [('articles', articles), ('world', world), ('publisher', publisher)])
        r.auth_or_abort()
        r.query = publish_filter(r.query).order_by('-created_date')
        r.prepare_query()
        set_theme(r, 'publisher', publisher.slug)
        set_theme(r, 'world', world.slug)
        return r

    def blog(self, publisher_, world_):
        r = self.index(publisher_, world_)
        r.args['per_page'] = 5
        r.args['view'] = 'list'
        r.query = r.query.filter(type='blogpost').order_by('-featured', '-created_date')
        r.template = 'world/article_blog.html'
        r.prepare_query()
        return r

    def random(self, publisher_, world_):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        # TODO ignores publisher for the moment
        articles = Article.objects(world=if_not_meta(world), status=PublishStatus.published,
                                   created_date__lte=datetime.utcnow())
        # TODO very inefficient random sample, use mongodb aggregation instead
        length = len(articles)
        if length:
            return redirect(url_for('world.ArticlesView:get', publisher_=publisher.slug, world_=world.slug,
                                    id=articles[random.randrange(length)].slug))
        else:
            return redirect(url_for('world.ArticlesView:index', publisher_=publisher.slug, world_=world.slug))

    def feed(self, publisher_, world_):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        feed = AtomFeed(_('Recent Articles in ') + world.title,
                        feed_url=request.url, url=request.url_root)
        articles = Article.objects(status=PublishStatus.published,
                                   created_date__lte=datetime.utcnow()).order_by('-created_date')[:10]
        for article in articles:
            feed.add(article.title, current_app.md._instance.convert(article.content),
                     content_type='html',
                     author=str(article.creator) if article.creator else 'System',
                     url=url_for('world.ArticlesView:get', publisher_=publisher.slug, world_=world.slug,
                                 id=article.slug, _external=True, _scheme=''),
                     updated=article.created_date,
                     published=article.created_date)
        return feed.get_response()

    def get(self, publisher_, world_, id):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)

        lang_options = world.languages or publisher.languages
        if lang_options:
            g.available_locales = lang_options

        # Special id post means we interpret this as intent=post (to allow simple routing to get)
        if id == 'post':
            r = ItemResponse(ArticlesView,
                             [('article', None), ('world', world), ('publisher', publisher)],
                             extra_args={'intent': 'post'})
            # check auth scoped to world or publisher, as we want to create new and use them as parent
            r.auth_or_abort(instance=world if world_ != 'meta' else publisher)
        else:
            r = ItemResponse(ArticlesView,
                             [('article', Article.objects(slug=id).first_or_404()), ('world', world),
                              ('publisher', publisher)])
            r.auth_or_abort()
            set_theme(r, 'article', r.article.theme or 'default')

        set_theme(r, 'publisher', publisher.slug)
        set_theme(r, 'world', world.slug)

        return r

    def post(self, publisher_, world_):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        lang_options = world.languages or publisher.languages
        if lang_options:
            g.available_locales = lang_options
        r = ItemResponse(ArticlesView,
                         [('article', None), ('world', world), ('publisher', publisher)],
                         method='post')
        # Check auth scoped to world or publisher, as we want to create new and use them as parent
        r.auth_or_abort(instance=world if world_ != 'meta' else publisher)
        set_theme(r, 'publisher', publisher.slug)
        set_theme(r, 'world', world.slug)

        article = Article()
        if not r.validate():
            flash(_("Error in form"), 'danger')
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(article)
        set_theme(r, 'article', article.theme or 'default')  # Incase we need to return to user

        try:
            r.commit(new_instance=article)
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.ArticlesView:get', id=article.slug, publisher_=publisher.slug,
                                                  world_=world.slug))

    def patch(self, publisher_, world_, id):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        article = Article.objects(slug=id).first_or_404()
        lang_options = world.languages or publisher.languages
        if lang_options:
            g.available_locales = lang_options
        r = ItemResponse(ArticlesView,
                         [('article', article), ('world', world), ('publisher', publisher)],
                         method='patch')
        r.auth_or_abort()
        set_theme(r, 'publisher', publisher.slug)
        set_theme(r, 'world', world.slug)
        set_theme(r, 'article', r.article.theme or 'default')

        if not r.validate():
            flash(_("Error in form"), 'danger')
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(article, request.form.keys())  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('world.ArticlesView:get', id=article.slug, publisher_=publisher.slug,
                                                  world_=world.slug))

    def delete(self, publisher_, world_, id):
        publisher = Publisher.objects(slug=publisher_).first_or_404()
        world = World.objects(slug=world_).first_or_404() if world_ != 'meta' else WorldMeta(publisher)
        article = Article.objects(slug=id).first_or_404()
        lang_options = world.languages or publisher.languages
        if lang_options:
            g.available_locales = lang_options
        r = ItemResponse(ArticlesView,
                         [('article', article), ('world', world), ('publisher', publisher)],
                         method='delete')
        r.auth_or_abort()
        set_theme(r, 'publisher', publisher.slug)
        set_theme(r, 'world', world.slug)
        set_theme(r, 'article', r.article.theme or 'default')

        r.commit()
        return redirect(
            r.args['next'] or url_for('world.ArticlesView:index', publisher_=publisher.slug, world_=world.slug))


class ArticleRelationsView(ResourceView):
    subdomain = '<publisher_>'
    route_base = '/<world_>/<article>'
    list_template = 'world/articlerelation_list.html'
    item_template = 'world/articlerelation_item.html'
    form_class = model_form(World, base_class=RacBaseForm, converter=RacModelConverter())
    access_policy = ResourceAccessPolicy()

    @route('/relations/')
    def index(self, world_):
        abort(501)  # Not implemented


@world_app.route('/')
def homepage():
    publishers = Publisher.objects()
    return render_template('homepage.html', publishers=publishers)


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
