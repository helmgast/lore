from flask import request, redirect, url_for, render_template, Blueprint, flash
from peewee import *
from wtfpeewee.orm import model_form
from models import Article, World
from resource import ResourceHandler
from raconteur import auth
from flask_peewee.utils import get_object_or_404, object_list, slugify

world = Blueprint('world', __name__, template_folder='templates')

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

@world.route('/')
def index():
    qr = World.select()
    return object_list('world/worlds.html', qr)

@world.route('/myworlds')
def myworlds():
    qr = Article.select()
    return object_list('world/index.html', qr)

@world.route('/<slug>/')
def world_detail(slug):
    world = get_object_or_404(World, World.slug == slug)
    world_articles = Article.select().where(Article.world == world)
    return object_list('world/world_detail.html', world_articles, world=world)

@world.route('/<worldslug>/<slug>/')
def article_detail(worldslug, slug):
    world = get_object_or_404(World, World.slug == worldslug)
    article = get_object_or_404(Article, Article.slug == slug)
    return articlehandler.handle_request(ResourceHandler.VIEW, article, world=world)

@world.route('/<worldslug>/<slug>/edit', methods=['GET', 'POST'])
def article_edit(worldslug, slug):
    world = get_object_or_404(World, World.slug == worldslug)
    article = get_object_or_404(Article, Article.slug == slug)
    return articlehandler.handle_request(ResourceHandler.EDIT, article, world=world)

@world.route('/<worldslug>/new', methods=['GET', 'POST'])
def article_new(worldslug):
    world = get_object_or_404(World, World.slug == worldslug)
    return articlehandler.handle_request(ResourceHandler.NEW, None, world=world)

@world.route('/<worldslug>/<slug>/delete/', methods=['GET', 'POST'])
@auth.login_required
def article_delete(worldslug, slug):
    #world = get_object_or_404(World, World.slug == worldslug)
    article = get_object_or_404(Article, Article.slug == slug)
    return articlehandler.handle_request(ResourceHandler.DELETE, article, world=world, redirect_url=url_for('world.world_detail', slug=worldslug))