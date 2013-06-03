from flask import request, redirect, url_for, render_template, Blueprint, flash
from peewee import *
from wtfpeewee.orm import model_form, Form, ModelConverter, FieldInfo
from models import Article, World, ArticleRelation, PersonArticle, PlaceArticle, EventArticle, MediaArticle, FractionArticle
from models import ARTICLE_DEFAULT, ARTICLE_MEDIA, ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT
from resource import ResourceHandler, ModelServer
from raconteur import auth, admin
from itertools import groupby
from datetime import datetime, timedelta
from flask_peewee.utils import get_object_or_404, object_list, slugify
from wtfpeewee.fields import ModelSelectField, ModelSelectMultipleField, ModelHiddenField, FormField,SelectQueryField
from wtforms.fields import FieldList, HiddenField
from flask_peewee.filters import FilterMapping, FilterForm, FilterModelConverter
from werkzeug.datastructures import ImmutableMultiDict

world_app = Blueprint('world', __name__, template_folder='templates')

# Template filter, will group a list by their initial title letter
def by_initials(objects):
  groups = []
  for k, g in groupby(objects, lambda o: o.title[0:1]):
    groups.append({'grouper':k, 'list':list(g)})
  return groups

# Template filter, will group a list by their article type_name
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

# Template filter, will group a list by creation date, as measure in delta from now
def by_time(objects):
  groups = []
  for k, g in groupby(objects, lambda o: prettydate(o.created_date)):
    groups.append({'grouper':k, 'list':list(g)})
  return groups

world_app.add_app_template_filter(by_initials)
world_app.add_app_template_filter(by_articletype)
world_app.add_app_template_filter(by_time)

# A slight modification of the normal ModelConverter (which automatically makes forms
# from Model classes). This will accept a "hidden" field argument which will then switch
# the form field type to ModelHidden, rather than a normal SelectQuery.
class WorldConverter(ModelConverter):
    def __init__(self):
        super(WorldConverter, self).__init__(additional={CharField:self.handle_textfield, TextField:self.handle_textfield})

    def handle_foreign_key(self, model, field, **kwargs):
        if field.null:
            kwargs['allow_blank'] = True
        if field.choices is not None:
            field_obj = SelectQueryField(query=field.choices, **kwargs)
        elif kwargs.pop('hidden',False):
            field_obj = ModelHiddenField(model=field.rel_model, **kwargs)
        else:
            query = kwargs.pop('query',None)
            field_obj = SelectQueryField(query=query if query else field.rel_model.select(), **kwargs)
        return FieldInfo(field.name, field_obj)

    def handle_textfield(self, model, field, **kwargs):
        if kwargs.pop('hidden',False): # from kwargs
            return FieldInfo(field.name, HiddenField(**kwargs))
        else:
            return FieldInfo(field.name, self.defaults[field.__class__](**kwargs))

# For later rference, create the forms for each article_type
personarticle_form = model_form(PersonArticle, converter=WorldConverter(), field_args={'article':{'hidden':True}})
mediaarticle_form = model_form(MediaArticle, converter=WorldConverter(), field_args={'article':{'hidden':True}})
eventarticle_form = model_form(EventArticle, converter=WorldConverter(), field_args={'article':{'hidden':True}})
placearticle_form = model_form(PlaceArticle, converter=WorldConverter(), field_args={'article':{'hidden':True}})
fractionarticle_form = model_form(FractionArticle, converter=WorldConverter(), field_args={'article':{'hidden':True}})

print "Form is %s" % personarticle_form

# Create article_relation form, but make sure we hide the from_article field.
articlerelation_form = model_form(ArticleRelation, converter=WorldConverter(), 
    field_args={'from_article':{'hidden':True},'relation_type':{'allow_blank':True}, 'to_relation':{'allow_blank':True}})

# This is a special form to handle Articles, where we know that it will have a special type of field:
# articletype. Article type is actually 5 separate fields in the model class, but only one of them should
# be not_null at any time. This means we need to take special care to ignore the null ones when validating
# (as the form will still render the field elements for all articletypes), and also when we populate an obj
# from the form, we want to only use the new actice type, and we want to remove any previous type object.
class ArticleForm(Form):
    def validate(self):
        self._errors = None
        success = True
        for name, field in self._fields.iteritems():
            # Exclude this fields, as only one of them should be validated
            if name not in ['personarticle', 'mediaarticle', 'eventarticle', 'placearticle', 'fractionarticle']:
                print "Validating %s" % name
                if not field.validate(self):
                    success = False
        if success:
            # Now, also validate one of the fields, depending on the type that we have
            if self.type.data == ARTICLE_DEFAULT:
                return success
            elif self.type.data == ARTICLE_MEDIA:
                print "Validating media"
                return self.mediaarticle.validate(self)
            elif self.type.data == ARTICLE_EVENT:
                return self.eventarticle.validate(self)
                print "Validating event"
            elif self.type.data == ARTICLE_PERSON:
                return self.personarticle.validate(self)
                print "Validating person"
            elif self.type.data == ARTICLE_PLACE:
                return self.placearticle.validate(self)
                print "Validating place"
            elif self.type.data == ARTICLE_FRACTION:
                return self.placearticle.validate(self)
                print "Validating place"
        return success

    def populate_obj(self, obj):
        old_type = obj.type
        old_type_obj = obj.get_type()
        old_typename = obj.type_name()+'article'

        # Do normal populate of all fields except FormFields
        for name, field in self._fields.iteritems():
            if name not in ['personarticle', 'mediaarticle', 'eventarticle', 'placearticle','fractionarticle']:
                print "Populating field %s with data %s" % (name, field.data)
                field.populate_obj(obj, name)
        
        # if old_type != obj.type:  
        #     # First clean up old reference
        #     print "We have changed type from %d to %d, old object was %s" % (old_type, obj.type, old_type_obj)
        #     if old_type_obj:
        #         print old_type_obj.delete_instance(recursive=True) # delete this and references to it
        typename = obj.type_name()+'article'
        if obj.type != ARTICLE_DEFAULT:
            field = self._fields[typename]
            new_model = obj.get_type().first()
            if not new_model:
                # Need to instantiate a new one if it didn't exist before!
                if typename=='personarticle':
                    new_model = PersonArticle()
                elif typename == 'mediaarticle':
                    new_model = MediaArticle()
                elif typename == 'eventarticle':
                    new_model = EventArticle()
                elif typename == 'placearticle':
                    new_model = PlaceArticle()
                print "Will populate %s with data %s" % (typename, field.form.data)
            else:
                field.form.populate_obj(new_model)
                new_model.save()
        else:
            print "Did not populate articletype as it's now DEFAULT"

article_form = model_form(Article, base_class=ArticleForm, exclude=['slug', 'created_date'], 
    converter=WorldConverter(), field_args={'world':{'hidden':True},'title':{'hidden':True},'content':{'hidden':True}})

# Need to add after creation otherwise the converter will interfere with them
article_form.personarticle = FormField(personarticle_form)
article_form.mediaarticle =  FormField(mediaarticle_form)
article_form.eventarticle =  FormField(eventarticle_form)
article_form.placearticle =  FormField(placearticle_form)
article_form.fractionarticle =  FormField(fractionarticle_form)
article_form.outgoing_relations = FieldList(FormField(articlerelation_form))

# Create servers to simplify our views
world_server = ModelServer(world_app, World, templatepath='world/')
article_server = ModelServer(world_app, Article, world_server, article_form)
# personarticle_server = ModelServer(world_app, PersonArticle, article_server, personarticle_form)
# mediaarticle_server = ModelServer(world_app, MediaArticle, article_server, mediaarticle_form)
# eventarticle_server = ModelServer(world_app, EventArticle, article_server, eventarticle_form)
# placearticle_server = ModelServer(world_app, PlaceArticle, article_server, placearticle_form)

@world_app.route('/')
def index():
    qr = World.select()
    return object_list('world/base.html', qr)

@world_app.route('/myworlds')
def myworlds():
    qr = Article.select()
    return object_list('world/index.html', qr)

@world_app.route('/<world_slug>/')
def view_world(world_slug):
    world = get_object_or_404(World, World.slug == world_slug)
    world_articles = world.articles
    return object_list('world/world_view.html', world_articles, world=world)

@world_app.route('/<world_slug>/list')
def list_article(world_slug):
    return redirect(url_for('.view_world', world_slug=world_slug))

@world_app.route('/<world_slug>/browse/<groupby>')
def world_browse(world_slug, groupby):
    world = get_object_or_404(World, World.slug == world_slug)
    if groupby == 'title':
        world_articles = Article.select().where(Article.world == world).order_by(Article.title.asc())
    elif groupby == 'type':
        world_articles = Article.select().where(Article.world == world).order_by(Article.type.asc())
    elif groupby == 'time':
        world_articles = Article.select().where(Article.world == world).order_by(Article.created_date.desc())
    else:
        abort(404)
    return object_list('world/world_browse.html', world_articles, world=world, groupby=groupby)

@world_app.route('/<world_slug>/<article_slug>/')
def view_article(world_slug, article_slug):
    world = get_object_or_404(World, World.slug == world_slug)
    article = get_object_or_404(Article, Article.slug == article_slug)
    return article_server.render('view', article, world=world)

@world_app.route('/<world_slug>/<article_slug>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_article(world_slug, article_slug):
    world = get_object_or_404(World, World.slug == world_slug)
    article = get_object_or_404(Article, Article.slug == article_slug)

    if request.method == 'GET':
        form = article_server.get_form('edit', article)
        print getattr(article, 'personarticle')
        # To make sure each form contains the article id of this article (as the fields are hidden)
        # We need to set the article
        form.personarticle.article.data = article
        form.eventarticle.article.data = article
        form.placearticle.article.data = article
        form.mediaarticle.article.data = article
        form.fractionarticle.article.data = article
        f = form[article.type_name()+'article']
        p = article.get_type().first()
        print f.form.data, p
        f.form.process(None, p)

        # This will limit some of the querys in the form to only allow articles from this world
        form.world.query = form.world.query.where(World.slug == world_slug)
        #form.outgoing_relations.append_entry({'from_article':article})
        for f in form.outgoing_relations:
            f.to_article.query = f.to_article.query.where(Article.world == world)
        return article_server.render('edit', article, form, world=world)
    elif request.method == 'POST':
        to_return = article_server.commit('edit', article, world=world)
        for o in article.outgoing_relations:
            o.save()
        return to_return

@world_app.route('/<world_slug>/new', methods=['GET', 'POST'])
@auth.login_required
def new_article(world_slug):
    world = get_object_or_404(World, World.slug == world_slug)
    if request.method == 'GET':
        return article_server.render('new', None, world=world)
    elif request.method == 'POST':
        return article_server.commit('new', None, world=world)

@world_app.route('/<world_slug>/<article_slug>/delete', methods=['GET', 'POST'])
@auth.login_required
def delete_article(world_slug, article_slug):
    world = get_object_or_404(World, World.slug == world_slug)
    article = get_object_or_404(Article, Article.slug == article_slug)
    if request.method == 'GET':
        return article_server.render('delete', article, world=world)
    elif request.method == 'POST':
        return article_server.commit('delete', article, world=world)

@world_app.route('/<world_slug>/<article_slug>/articletype/new', methods=['GET', 'POST'])
@auth.login_required
def articletype_new(world_slug, article_slug, articletype_id):
    world = get_object_or_404(World, World.slug == world_slug)
    article = get_object_or_404(Article, Article.slug == article_slug)
    if article.type == ARTICLE_DEFAULT:
        abort(404) # TODO, proper error
    elif article.type == ARTICLE_PERSON:
        articletype = get_object_or_404(PersonArticle, PersonArticle.id == articletype_id)
        server = personarticle_server
    elif article.type == ARTICLE_EVENT:
        articletype = get_object_or_404(EventArticle, EventArticle.id == articletype_id)
        server = eventarticle_server
    elif article.type == ARTICLE_PLACE:
        articletype = get_object_or_404(PlaceArticle, PlaceArticle.id == articletype_id)
        server = placearticle_server
    elif article.type == ARTICLE_MEDIA:
        articletype = get_object_or_404(MediaArticle, MediaArticle.id == articletype_id)
        server = mediaarticle_server
    else:
        abort(404) # TODO, proper error
    if request.method == 'GET':
        return server.render('edit', articletype, world=world, article=article)
    elif request.method == 'POST':
        return server.commit('edit', articletype, world=world, article=article)
