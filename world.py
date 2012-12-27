import datetime

from flask import request, redirect, url_for, render_template, Blueprint, flash
from peewee import *
from wtfpeewee.orm import model_form
from models import Article, World
from resource import ResourceHandler

from flask_peewee.utils import get_object_or_404, object_list, slugify

from auth import auth

world = Blueprint('world', __name__, template_folder='templates')

class WorldHandler(ResourceHandler):
    def get_redirect_url(self, instance):
        return url_for(self.route, slug=instance.slug)

    def allowed(self, op, user, instance=None):
        if user:
            return True
        elif op == ResourceHandler.VIEW:
            return True
        else:
            return False

worldhandler = WorldHandler(
        World,
        model_form(World, exclude=['slug']),
        'world/world_page.html',
        'world.world_detail')

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

@world.route('/<worldslug>/<title>/', methods=['GET', 'POST'])
@auth.login_required
def article_detail(worldslug, title):
    world = get_object_or_404(World, World.slug == worldslug)

    WikiForm = model_form(Article, only=('title', 'content',))

    try:
        article = Article.get(title=title)
    except Article.DoesNotExist:
        article = Article(title=title)

    if request.method == 'POST':
        form = WikiForm(request.form, obj=article)
        if form.validate():
            form.populate_obj(article)
            article.save()
            flash('Your changes have been saved')
            return redirect(url_for('world.detail', title=article.title))
        else:
            flash('There were errors with your submission')
    else:
        form = WikiForm(obj=article)

    return render_template('world/article_detail.html', article=article, form=form, world=world)


@world.route('<worldslug>/<title>/delete/', methods=['GET', 'POST'])
@auth.login_required
def article_delete(worldslug, title):
    article = get_object_or_404(Article, title=title)
    if request.method == 'POST':
        article.delete_instance()
        return redirect(url_for('world.index'))

    return render_template('world/article_delete.html', article=article)

