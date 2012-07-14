import datetime
import re

from flask import request, redirect, url_for, render_template, Blueprint, flash, Markup
from peewee import *
from wtfpeewee.orm import model_form

from flask_peewee.rest import RestResource
from flask_peewee.utils import get_object_or_404, object_list

from app import db
from api import api
from auth import auth

class Article(db.Model):
    name = CharField()
    content = TextField()
    modified_date = DateTimeField()

    class Meta:
        ordering = (('modified_date', 'desc'),)

    def __unicode__(self):
        return self.name

    def save(self):
        self.modified_date = datetime.datetime.now()
        return super(Article, self).save()

world = Blueprint('world', __name__, template_folder='templates')
Article.create_table(fail_silently=True)

@world.route('/')
@auth.login_required
def index():
    print "Index"
    qr = Article.select()
    return object_list('world/index.html', qr)

@world.route('/<name>/', methods=['GET', 'POST'])
@auth.login_required
def detail(name):
    WikiForm = model_form(Article, only=('name', 'content',))

    try:
        article = Article.get(name=name)
    except Article.DoesNotExist:
        article = Article(name=name)

    if request.method == 'POST':
        form = WikiForm(request.form, obj=article)
        if form.validate():
            form.populate_obj(article)
            article.save()
            flash('Your changes have been saved')
            return redirect(url_for('world.detail', name=article.name))
        else:
            flash('There were errors with your submission')
    else:
        form = WikiForm(obj=article)

    return render_template('world/detail.html', article=article, form=form)

@world.route('/<name>/delete/', methods=['GET', 'POST'])
@auth.login_required
def delete(name):
    article = get_object_or_404(Article, name=name)
    if request.method == 'POST':
        article.delete_instance()
        return redirect(url_for('world.index'))

    return render_template('world/delete.html', article=article)