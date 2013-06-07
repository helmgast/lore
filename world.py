from flask import request, redirect, url_for, render_template, Blueprint, flash
from peewee import *
from wtfpeewee.orm import model_form, Form, ModelConverter, FieldInfo
from models import Article, World, ArticleRelation, PersonArticle, PlaceArticle, EventArticle, MediaArticle, FractionArticle, ArticleGroup, Group
from models import ARTICLE_DEFAULT, ARTICLE_MEDIA, ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT, ARTICLE_TYPES
from resource import ResourceHandler, ModelServer
from raconteur import auth, admin
from itertools import groupby
from datetime import datetime, timedelta
from flask_peewee.utils import get_object_or_404, object_list, slugify
from wtfpeewee.fields import ModelSelectField, SelectMultipleQueryField, ModelHiddenField, FormField,SelectQueryField
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
        elif kwargs.pop('multiple', False):
            query = kwargs.pop('query',None)
            field_obj = SelectMultipleQueryField(query=query if query else field.rel_model.select(), **kwargs)
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

# Create article_relation form, but make sure we hide the from_article field.
articlerelation_form = model_form(ArticleRelation, converter=WorldConverter(), 
    field_args={'from_article':{'hidden':True},'relation_type':{'allow_blank':True,'blank_text':u' '}, 'to_article':{'allow_blank':True,'blank_text':u' '}})

articlegroup_form = model_form(ArticleGroup, converter=WorldConverter(),
    field_args={'article':{'hidden':True},'group':{'multiple':True}})

class ArticleTypeFormField(FormField):
    def validate(self, form, extra_validators=tuple()):
        if extra_validators:
            raise TypeError('FormField does not accept in-line validators, as it gets errors from the enclosed form.')
        print "Validating ArticleType form field, form type is %d (%s), == name %s" % (form.type.data, ARTICLE_TYPES[form.type.data][1]+'article', self.name)
        if form.type.data > 0 and (ARTICLE_TYPES[form.type.data][1]+'article')==self.name:
            return self.form.validate()
        else: # Only validate this field if it corresponds to current type, otherwise ignore
            return True

# This is a special form to handle Articles, where we know that it will have a special type of field:
# articletype. Article type is actually 5 separate fields in the model class, but only one of them should
# be not_null at any time. This means we need to take special care to ignore the null ones when validating
# (as the form will still render the field elements for all articletypes), and also when we populate an obj
# from the form, we want to only use the new actice type, and we want to remove any previous type object.
class ArticleForm(Form):
    sub_fields = ['personarticle', 'mediaarticle', 'eventarticle', 'placearticle', 'fractionarticle','outgoing_relations']

    def pre_validate(self):
        self._errors = None
        success = True
        for name, field in self._fields.iteritems():
            # Exclude this fields, as only one of them should be validated
            if name not in self.sub_fields:
                if not field.validate(self):
                    success = False
        self.prevalidated = True
        return success

    def validate(self):
        if not hasattr(self, 'prevalidated') or not self.prevalidated:
            success = self.pre_validate()
        else:
            success = True
        for name, field in self._fields.iteritems():
            # Exclude this fields, as only one of them should be validated
            if name in self.sub_fields:
                if not field.validate(self):
                    success = False
        return success

    def pre_populate_obj(self, obj):
        # Do normal populate of all fields except FormFields
        for name, field in self._fields.iteritems():
            if name not in self.sub_fields:
                print "Pre-populating field %s with data %s" % (name, field.data)
                field.populate_obj(obj, name)
        self.prepopulated = True
        
    def populate_obj(self, obj):
        if not hasattr(self, 'prepopulated') or not self.prepopulated:
            self.pre_populate_obj(obj)
        typename = obj.type_name()+'article'
        if obj.type != ARTICLE_DEFAULT:
            field = self._fields[typename]
            new_model = obj.get_type()
            print "Current type is %s, obj is %s" % (typename, new_model)
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
                elif typename == 'fractionarticle':
                    new_model = FractionArticle()    
                print "Will populate %s with data %s" % (typename, field.form.data)
            field.form.populate_obj(new_model)
            new_model.save()
        else:
            print "Did not populate articletype as it's now DEFAULT"
        self._fields['outgoing_relations'].populate_obj(obj, 'outgoing_relations')

article_form = model_form(Article, base_class=ArticleForm, exclude=['slug', 'created_date'], 
    converter=WorldConverter(), field_args={'world':{'hidden':True},'title':{'hidden':True},'content':{'hidden':True}})

class ArticleRelationFormField(FormField):
    def populate_obj(self, obj, name):
        print "This field has data %s, trying to write it to attribute %s of obj %s, currently %s (_obj is %s)" % (self.data, name, obj, getattr(obj, 'data'), self._obj)
        candidate = getattr(obj, name, None)
        if candidate is None:
            if self._obj is None:
                self._obj = ArticleRelation()
                #raise TypeError('populate_obj: cannot find a value to populate from the provided obj or input data/defaults')
            candidate = self._obj
            setattr(obj, name, candidate)
        self.form.populate_obj(candidate)
        candidate.save()

# Need to add after creation otherwise the converter will interfere with them
article_form.personarticle = ArticleTypeFormField(personarticle_form)
article_form.mediaarticle =  ArticleTypeFormField(mediaarticle_form)
article_form.eventarticle =  ArticleTypeFormField(eventarticle_form)
article_form.placearticle =  ArticleTypeFormField(placearticle_form)
article_form.fractionarticle =  ArticleTypeFormField(fractionarticle_form)
article_form.outgoing_relations = FieldList(ArticleRelationFormField(articlerelation_form))
article_form.articlegroups = FormField(articlegroup_form)


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
        if article.type > 0:
            # TODO for some reason the prefill of article type has to be done manually
            f = form[article.type_name()+'article']
            f.form.process(None, article.get_type())
        form.articlegroups.group.data = [a.group for a in article.articlegroups]
        form.articlegroups.article.data = article
        # This will limit some of the querys in the form to only allow articles from this world
        form.world.query = form.world.query.where(World.slug == world_slug)
        for f in form.outgoing_relations:
            f.to_article.query = f.to_article.query.where(Article.world == world).where(Article.id != article.id)
        return article_server.render('edit', article, form, world=world)
    elif request.method == 'POST':
        form = article_server.get_form('edit', article, request.form)
        print form.articlegroups.data
        art_groups = {a.group.id:a for a in article.articlegroups}
        for g in form.articlegroups.data['group']:
            if g.id not in art_groups:
                ArticleGroup.create(article=article, group=g)
       # already_groups = ArticleGroup.select().where(ArticleGroup.article == article, ArticleGroup.group << form.articlegroups.data)
       #  for g in form.articlegroups.data:
       #      if 
       #      ArticleGroup.create(article=article, group=g)
        before_relations = {a.id:a for a in article.outgoing_relations}
        article.remove_old_type(form.type.data) # remove old typeobj if needed
        # We will set the default article relation on the chosen articletype
        if form.type.data > 0:
            form[article.type_name(form.type.data )+'article'].article.data = article
        form.articlegroups.article.data = article
        to_return = article_server.commit('edit', article, form, world=world)
        for o in article.outgoing_relations:
            o.save()
            del before_relations[o.id] # remove it from the list of relations we may need to delete
        for a in before_relations.values():
            a.delete_instance() # delete the relations that were not in the list after form processing
        for g in art_groups:
            if art_groups[g] not in form.articlegroups.data:
                art_groups[g].delete_instance()
        return to_return

@world_app.route('/<world_slug>/<article_slug>/articlerelations/new', methods=['GET'])
@auth.login_required
def new_articlerelation(world_slug, article_slug):
    world = get_object_or_404(World, World.slug == world_slug)
    article = get_object_or_404(Article, Article.slug == article_slug)
    form = article_server.get_form('edit', article)
    nr = request.args.get('nr')
    nr = max(1,int(nr))
    for k in range(0,nr):
        print k
        form.outgoing_relations.append_entry({'from_article':article})
        form.outgoing_relations[-1].to_article.query = form.outgoing_relations[-1].to_article.query.where(Article.world == world)
    return render_template('models/articlerelation_view.html', op='new', articlerelation_form=form.outgoing_relations[-1])

@world_app.route('/<world_slug>/new', methods=['GET', 'POST'])
@auth.login_required
def new_article(world_slug):
    world = get_object_or_404(World, World.slug == world_slug)
    if request.method == 'GET':
        return article_server.render('new', None, world=world)
    elif request.method == 'POST':
        form = article_server.get_form('new', req_form=request.form)
        if form.pre_validate():
            article = Article(world=world)
            # We need special prepopulate to create the Article object fully before we try to create dependent objects
            form.pre_populate_obj(article)
            article.save()
            form[article.type_name(form.type.data )+'article'].article.data = article
            return article_server.commit('new', article, form, world=world)
    else:
        abort(501)

@world_app.route('/<world_slug>/<article_slug>/delete', methods=['GET', 'POST'])
@auth.login_required
def delete_article(world_slug, article_slug):
    world = get_object_or_404(World, World.slug == world_slug)
    article = get_object_or_404(Article, Article.slug == article_slug)
    if request.method == 'GET':
        return article_server.render('delete', article, world=world)
    elif request.method == 'POST':
        return article_server.commit('delete', article, world=world)
