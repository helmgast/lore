from flask import request, redirect, url_for, render_template, Blueprint, flash
from peewee import *
from wtfpeewee.orm import model_form
from models import Article, World, ArticleRelation, PersonArticle, PlaceArticle, EventArticle, MediaArticle, ARTICLE_TYPES
from resource import ResourceHandler, ModelServer
from raconteur import auth, admin
from itertools import groupby
from datetime import datetime, timedelta
from flask_peewee.utils import get_object_or_404, object_list, slugify
from flask_peewee.forms import BaseModelConverter, ChosenAjaxSelectWidget, LimitedModelSelectField
from wtfpeewee.fields import ModelSelectField, ModelSelectMultipleField, ModelHiddenField
from flask_peewee.filters import FilterMapping, FilterForm, FilterModelConverter

world = Blueprint('world', __name__, template_folder='templates')

def debugprint(s):
  print s
  return s
world.add_app_template_filter(debugprint)

def by_initials(objects):
  groups = []
  for k, g in groupby(objects, lambda o: o.title[0:1]):
    groups.append({'grouper':k, 'list':list(g)})
  return groups

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

def by_time(objects):
  groups = []
  for k, g in groupby(objects, lambda o: prettydate(o.created_date)):
    groups.append({'grouper':k, 'list':list(g)})
  return groups

world.add_app_template_filter(by_initials)
world.add_app_template_filter(by_articletype)
world.add_app_template_filter(by_time)


class WorldHandler(ResourceHandler):
    def get_redirect_url(self, instance):
        return url_for(self.route, slug=instance.slug)

    def allowed(self, op, user, instance=None):
        if op == ResourceHandler.VIEW: # currently only allow viewing
            return True
        else:
            return False

worldhandler = WorldHandler(
        World,
        model_form(World, exclude=['slug']),
        'world/world_page.html',
        'world.world_detail')

class ArticleHandler(ResourceHandler):
    def get_redirect_url(self, instance):
        return url_for(self.route, slug=instance.slug, worldslug=instance.world.slug)

    def allowed(self, op, user, instance=None):
        if op == ResourceHandler.VIEW:
            return True
        elif user:
            return True
        else:
            return False

articlehandler = ArticleHandler(
        Article,
        model_form(Article, exclude=['slug', 'created_date']),
        'world/article_detail.html',
        'world.article_detail')

class ArticleRelationHandler(ResourceHandler):
    def get_redirect_url(self, instance):
        return url_for(self.route, slug=instance.slug, worldslug=instance.world.slug)

    def allowed(self, op, user, instance=None):
        if op == ResourceHandler.VIEW:
            return True
        elif user:
            return True
        else:
            return False

article_relations_handler = ArticleRelationHandler(
        ArticleRelation,
        model_form(ArticleRelation),
        'world/article_relations_detail.html',
        'world.article_detail')

personarticleform = model_form(PersonArticle)

class AdminModelConverter(BaseModelConverter):
    def __init__(self, additional=None):
        super(AdminModelConverter, self).__init__(additional)

    def handle_foreign_key(self, model, field, **kwargs):
        if field.null:
            kwargs['allow_blank'] = True

#        if field.name in (self.model_admin.foreign_key_lookups or ()):
#            form_field = ModelHiddenField(model=field.rel_model, **kwargs)
#        else:
        form_field = ModelSelectField(model=field.rel_model, **kwargs)
        return field.name, form_field


#----------
world_test = ModelServer(world, World, {'view':'world/world_view.html', 'edit':'world/world_view.html'})

article_test = ModelServer(world, Article, {'view':'world/article_view.html', 'edit':'world/article_view.html'}, 
    world_test, model_form(Article, exclude=['slug', 'created_date'], converter=AdminModelConverter()))

personarticle_test = ModelServer(world, PersonArticle, {}, article_test)
mediaarticle_test = ModelServer(world, MediaArticle, {}, article_test)
eventarticle_test = ModelServer(world, EventArticle, {}, article_test)
placearticle_test = ModelServer(world, PlaceArticle, {}, article_test)

@world.route('/')
def index():
    qr = World.select()
    return object_list('world/world.html', qr)

@world.route('/myworlds')
def myworlds():
    qr = Article.select()
    return object_list('world/index.html', qr)

# @world.route('/<slug>/')
# def world_detail(slug):
#     world = get_object_or_404(World, World.slug == slug)
#     world_articles = Article.select().where(Article.world == world)
#     return object_list('world/world_detail.html', world_articles, world=world)

@world.route('/<slug>/browse/<groupby>')
def world_browse(slug, groupby):
    world = get_object_or_404(World, World.slug == slug)
    if groupby == 'title':
        world_articles = Article.select().where(Article.world == world).order_by(Article.title.asc())
    elif groupby == 'type':
        world_articles = Article.select().where(Article.world == world).order_by(Article.type.asc())
    elif groupby == 'time':
        world_articles = Article.select().where(Article.world == world).order_by(Article.created_date.desc())
    else:
        abort(404)
    return object_list('world/world_browse.html', world_articles, world=world, groupby=groupby)

# @world.route('/<worldslug>/<slug>/')
# def article_detail(worldslug, slug):
#     world = get_object_or_404(World, World.slug == worldslug)
#     article = get_object_or_404(Article, Article.slug == slug)
#     articletype = article.get_type()
#     articlerelations = ArticleRelations.select().where(ArticleRelations.from_article == article).order_by(ArticleRelations.relation_type.asc());
#     return articlehandler.handle_request(ResourceHandler.VIEW, article, world=world, articletype=articletype,
#         articlerelations=articlerelations, type=ARTICLE_TYPES[article.type][1])

# @world.route('/<worldslug>/<slug>/edit', methods=['GET', 'POST'])
# def article_edit(worldslug, slug):
#     world = get_object_or_404(World, World.slug == worldslug)
#     article = get_object_or_404(Article, Article.slug == slug)
#     articletype = article.get_type()
#     articlerelations = ArticleRelations.select().where(ArticleRelations.from_article == article).order_by(ArticleRelations.relation_type.asc());
#     return articlehandler.handle_request(ResourceHandler.EDIT, article, world=world, articletype=articletype,
#         articlerelations=articlerelations, type=ARTICLE_TYPES[article.type][1])

# @world.route('/<worldslug>/new', methods=['GET', 'POST'])
# def article_new(worldslug):
#     world = get_object_or_404(World, World.slug == worldslug)
#     return articlehandler.handle_request(ResourceHandler.NEW, None, world=world)

# @world.route('/<worldslug>/<slug>/delete/', methods=['GET', 'POST'])
# @auth.login_required
# def article_delete(worldslug, slug):
#     #world = get_object_or_404(World, World.slug == worldslug)
#     article = get_object_or_404(Article, Article.slug == slug)
#     return articlehandler.handle_request(ResourceHandler.DELETE, article, world=world, redirect_url=url_for('world.world_detail', slug=worldslug))

# @world.route('/<worldslug>/<slug>/relate', methods=['GET', 'POST'])
# def article_relate(worldslug, slug):
#     world = get_object_or_404(World, World.slug == worldslug)
#     article = get_object_or_404(Article, Article.slug == slug)
#     relations = ArticleRelations.select().where(ArticleRelations.from_article == article).order_by(ArticleRelations.relation_type.asc());
#     return object_list('world/article_relations_detail.html', relations, world=world, article=article)

