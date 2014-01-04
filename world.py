from flask import request, redirect, url_for, render_template, Blueprint, flash
from peewee import *
from wtfpeewee.orm import model_form, Form, ModelConverter, FieldInfo
from model.world import Article, World, ArticleRelation, PersonArticle, PlaceArticle, EventArticle, MediaArticle, FractionArticle, ARTICLE_DEFAULT, ARTICLE_MEDIA, ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT, ARTICLE_TYPES
from model.user import Group
from flask.views import View

from resource import ResourceHandler, ModelServer, ResourceHandler2, ResourceAccessStrategy
from raconteur import auth
from itertools import groupby
from datetime import datetime, timedelta
from wtfpeewee.fields import ModelSelectField, SelectMultipleQueryField, ModelHiddenField, FormField, SelectQueryField
from wtforms.fields import FieldList, HiddenField
from werkzeug.datastructures import ImmutableMultiDict

# world_app = Blueprint('world', __name__, template_folder='templates')
# 
# world_handler = ResourceHandler2(ResourceAccessStrategy(World, 'worlds'))
# world_handler.register_urls(world_app)
# 
# article_handler = ResourceHandler2(ResourceAccessStrategy(Article, 'articles', parent_strategy=world_handler.strategy))
# article_handler.register_urls(world_app)
# 
# 
# # Template filter, will group a list by their initial title letter
# def by_initials(objects):
#   groups = []
#   for k, g in groupby(objects, lambda o: o.title[0:1]):
#     groups.append({'grouper':k, 'list':list(g)})
#   return groups
# 
# # Template filter, will group a list by their article type_name
# def by_articletype(objects):
#   groups = []
#   for k, g in groupby(objects, lambda o: o.type_name()):
#     groups.append({'grouper':k, 'list':list(g)})
#   return groups
# 
# def prettydate(d):
#     diff = timedelta()
#     diff = datetime.utcnow() - d
#     if diff.days < 1:
#         return 'Today'
#     elif diff.days < 7:
#         return 'Last week'
#     elif diff.days < 31:
#         return 'Last month'
#     elif diff.days < 365:
#         return 'Last year'
#     else:
#         return 'Older'
# 
# # Template filter, will group a list by creation date, as measure in delta from now
# def by_time(objects):
#   groups = []
#   for k, g in groupby(objects, lambda o: prettydate(o.created_date)):
#     groups.append({'grouper':k, 'list':list(g)})
#   return groups
# 
# world_app.add_app_template_filter(by_initials)
# world_app.add_app_template_filter(by_articletype)
# world_app.add_app_template_filter(by_time)
# 
# 
# class ArticleGroupSelectMultipleQueryField(SelectMultipleQueryField):
#     '''
#     A single multi-select field that represents a list of ArticleGroups.
#     '''
# 
#     def iter_choices(self):
#         # Although the field holds ArticleGroups, we will allow choices from all combinations of groups and types.
#         for obj in Group.objects:
#             yield ('%d-%d' % (obj.get_id(),GROUP_MASTER), self.get_label(obj)+' (masters)', self.has_articlegroup(obj.get_id(), GROUP_MASTER))
#             yield ('%d-%d' % (obj.get_id(),GROUP_PLAYER), self.get_label(obj)+' (all)', self.has_articlegroup(obj.get_id(), GROUP_PLAYER))
# 
#     # Checks if tuple of group_id and type matches an existing ArticleGroup in this field
#     def has_articlegroup(self, group_id, type):
#         if self._data:
#             for ag in self._data:
#                 if ag.group.id == group_id and ag.type == type:
#                     return True
#         return False
# 
#     def process_formdata(self, valuelist):
#         if valuelist:
#             self._data = []
#             self._formdata = []
#             for v in valuelist:
#                 g_id, g_type = v.split('-')
#                 g_id = int(g_id)
#                 # We don't know article yet, it has to be set manually
#                 self._formdata.append({'article':None, 'group':g_id,'type':g_type})
#             # self._formdata = map(int, valuelist)
#         else:
#             self._formdata = []
# 
#     # def get_model_list(self, pk_list):
#     #     # if pk_list:
#     #     #     return list(self.query.where(self.model._meta.primary_key << pk_list))
#     #     return []
# 
#     def _get_data(self):
#         # if self._formdata is not None:
#         #     self._set_data(self.get_model_list(self._formdata))
#         return self._data or []
# 
#     def _set_data(self, data):
#         if hasattr(data, '__iter__'):
#             self._data = list(data)
#         else:
#             self._data = data
#         self._formdata = None
# 
#     data = property(_get_data, _set_data)
# 
#     # def pre_validate(self, form):
#     #     if self.data:
#     #         id_list = [m.get_id() for m in self.data]
#     #         if id_list and not self.query.where(self.model._meta.primary_key << id_list).count() == len(id_list):
#     #             raise ValidationError(self.gettext('Not a valid choice'))
# 
# # For later rference, create the forms for each article_type
# personarticle_form = model_form(PersonArticle)
# mediaarticle_form = model_form(MediaArticle)
# eventarticle_form = model_form(EventArticle)
# placearticle_form = model_form(PlaceArticle)
# fractionarticle_form = model_form(FractionArticle)
# 
# # Create article_relation form, but make sure we hide the from_article field.
# articlerelation_form = model_form(ArticleRelation, converter=WorldConverter(), 
#     field_args={'from_article':{'hidden':True},'relation_type':{'allow_blank':True,'blank_text':u' '}, 'to_article':{'allow_blank':True,'blank_text':u' '}})
# 
# class ArticleTypeFormField(FormField):
#     def validate(self, form, extra_validators=tuple()):
#         if extra_validators:
#             raise TypeError('FormField does not accept in-line validators, as it gets errors from the enclosed form.')
#         print "Validating ArticleType form field, form type is %d (%s), == name %s" % (form.type.data, ARTICLE_TYPES[form.type.data][1]+'article', self.name)
#         if form.type.data > 0 and (ARTICLE_TYPES[form.type.data][1]+'article')==self.name:
#             return self.form.validate()
#         else: # Only validate this field if it corresponds to current type, otherwise ignore
#             return True
# 
# class ArticleRelationFormField(FormField):
#     def populate_obj(self, obj, name):
#         # print "This field has data %s, trying to write it to attribute %s of obj %s, currently %s (_obj is %s)" % (self.data, name, obj, getattr(obj, 'data'), self._obj)
#         candidate = getattr(obj, name, None)
#         if candidate is None:
#             if self._obj is None:
#                 self._obj = ArticleRelation()
#                 #raise TypeError('populate_obj: cannot find a value to populate from the provided obj or input data/defaults')
#             candidate = self._obj
#             setattr(obj, name, candidate)
#         self.form.populate_obj(candidate)
#         candidate.save()
# 
# # Need to add after creation otherwise the converter will interfere with them
# article_form.personarticle = ArticleTypeFormField(personarticle_form)
# article_form.mediaarticle =  ArticleTypeFormField(mediaarticle_form)
# article_form.eventarticle =  ArticleTypeFormField(eventarticle_form)
# article_form.placearticle =  ArticleTypeFormField(placearticle_form)
# article_form.fractionarticle =  ArticleTypeFormField(fractionarticle_form)
# article_form.outgoing_relations = FieldList(ArticleRelationFormField(articlerelation_form))
# article_form.articlegroups = ArticleGroupSelectMultipleQueryField(query=ArticleGroup.select())
# 
# def allowed_article(op, user, model_obj=None):
#     print "Testing allowed %s for %s" % (op, user)
#     if op=='list':
#         return True
#     elif op=='new' and user:
#         return True
#     elif model_obj and model_obj.creator == user:
#         return True #creator has full rights
#     elif user and user.username == 'admin':
#         return True
#     elif op=='view' or op=='edit': # we are not creator but we want to edit or view
#         ags = list(model_obj.articlegroups)
#         players_allowed = {}
#         groups_in_ags = []
#         for ag in ags:
#             if ag.type == GROUP_PLAYER: # allows players as well as masters
#                 players_allowed[ag.group.id] = ag
#             groups_in_ags.append(ag.group)
#         if not ags: #empty list
#             return True
#         else:
#             # If the user is a member of a group in ArticleGroups and also has the same status, it's ok
#             gms = list(GroupMember.select().where(GroupMember.member == user, GroupMember.group << groups_in_ags))
#             print gms
#             for gm in gms:
#                 if gm.status == GROUP_MASTER:
#                     return True # this user is master in any of these groups and will therefore have full access
#                 if gm.group.id in players_allowed:
#                     return True
#     return False
# 
# # Create servers to simplify our views
# world_server = ModelServer(world_app, World, templatepath='world/')
# article_server = ModelServer(world_app, Article, world_server, article_form, allowed_func=allowed_article)
# 
# @world_app.route('/')
# def index():
#     qr = World.select()
#     return render_template('world/base.html', qr)
# 
# @world_app.route('/myworlds')
# def myworlds():
#     qr = Article.select()
#     return render_template('world/index.html', qr)
# 
# @world_app.route('/<world_slug>/')
# def view_world(world_slug):
#     world = World.objects.get_or_404(slug=world_slug)
#     world_articles = world.articles
#     return render_template('world/world_view.html', world_articles, world=world)
# 
# @world_app.route('/<world_slug>/list')
# def list_article(world_slug):
#     return redirect(url_for('.view_world', world_slug=world_slug))
# 
# @world_app.route('/<world_slug>/browse/<groupby>')
# def world_browse(world_slug, groupby):
#     world = World.objects.get_or_404(slug=world_slug)
#     if groupby == 'title':
#         world_articles = Article.objects(world=world).order_by('title')
#     elif groupby == 'type':
#         world_articles = Article.objects(world=world).order_by('type')
#     elif groupby == 'time':
#         world_articles = Article.objects(world=world).order_by('-created_date') # descending order
#     elif groupby == 'relation':
#         world_articles = Article.objects(world=world).order_by('-created_date') # descending order
#         return render_template('models/articlerelation_list.html', world_articles, world=world, groupby=groupby)
#     else:
#         abort(404)
#     return render_template('world/world_browse.html', world_articles, world=world, groupby=groupby)
# 
# @world_app.route('/<world_slug>/<article_slug>/')
# def view_article(world_slug, article_slug):
#     world = World.objects.get_or_404(slug=world_slug)
#     article = Article.objects.get_or_404(slug=article_slug)
#     return article_server.render('view', article, world=world)
# 
# @world_app.route('/<world_slug>/<article_slug>/edit', methods=['GET', 'POST'])
# @auth.login_required
# def edit_article(world_slug, article_slug):
#     world = World.objects.get_or_404(slug=world_slug)
#     article = Article.objects.get_or_404(slug=article_slug)
#     if request.method == 'GET':
#         form = article_server.get_form('edit', article)
#         if article.type > 0:
#             # TODO for some reason the prefill of article type has to be done manually
#             f = form[article.type_name()+'article']
#             f.form.process(None, article.get_type())
# 
#         # This will limit some of the querys in the form to only allow articles from this world
#         form.world.query = form.world.query.where(World.slug == world_slug)
#         for f in form.outgoing_relations:
#             f.to_article.query = f.to_article.query.where(Article.world == world).where(Article.id != article.id)
#         return article_server.render('edit', article, form, world=world)
#     elif request.method == 'POST':
#         form = article_server.get_form('edit', article, request.form)
#         # print form.articlegroups._data
#         # Read previous article groups
#         art_groups = {a.group.id:a for a in article.articlegroups}
# 
#         # TODO Extremely hacky way of getting articlegroups from a single multi-select
#         given_ids = []
#         for ag in form.articlegroups._formdata:
#             if ag['group'] not in art_groups: # Create new for the ones that didn't exist before
#                 ArticleGroup.create(article=article, group=Group.get(Group.id == ag['group']), type = ag['type'])
#             given_ids.append(ag['group'])
#         before_relations = {a.id:a for a in article.outgoing_relations}
#         article.remove_old_type(form.type.data) # remove old typeobj if needed
#         # We will set the default article relation on the chosen articletype
#         if form.type.data > 0:
#             # Set the current article as default to validate correctly
#             form[article.type_name(form.type.data )+'article'].article.data = article
#         to_return = article_server.commit('edit', article, form, world=world)
#         for o in article.outgoing_relations:
#             o.save()
#             if o.id in before_relations:
#                 del before_relations[o.id] # remove it from the list of relations we may need to delete
#         for a in before_relations.values():
#             a.delete_instance() # delete the relations that were not in the list after form processing
#         for ag in art_groups.values():
#             if ag.group.id not in given_ids:
#                 ag.delete_instance()
#         return to_return
# 
# @world_app.route('/<world_slug>/<article_slug>/articlerelations/new', methods=['GET'])
# @auth.login_required
# def new_articlerelation(world_slug, article_slug):
#     world = World.objects.get_or_404(slug=world_slug)
#     article = Article.objects.get_or_404(slug=article_slug)
#     form = article_server.get_form('edit', article)
#     nr = request.args.get('nr')
#     nr = max(1,int(nr))
#     for k in range(0,nr+1):
#         form.outgoing_relations.append_entry({'from_article':article})
#         form.outgoing_relations[-1].to_article.query = form.outgoing_relations[-1].to_article.query.where(Article.world == world).where(Article.id != article.id)
#     return render_template('models/articlerelation_view.html', op='new', articlerelation_form=form.outgoing_relations[-1])
# 
# @world_app.route('/<world_slug>/new', methods=['GET', 'POST'])
# @auth.login_required
# def new_article(world_slug):
#     world = World.objects.get_or_404(slug=world_slug)
#     if request.method == 'GET':
#         return article_server.render('new', None, world=world)
#     elif request.method == 'POST':
#         form = article_server.get_form('new', req_form=request.form)
#         form.creator.data = auth.get_logged_in_user()
#         if form.pre_validate():
#             article = Article(world=world)
#             # We need special prepopulate to create the Article object fully before we try to create dependent objects
#             form.pre_populate_obj(article)
#             article.save()
#             if form.type.data > 0:
#                 form[article.type_name(form.type.data )+'article'].article.data = article
#             return article_server.commit('new', article, form, world=world)
#         else:
#             s = '%s' % form.errors
#             return s
# 
# @world_app.route('/<world_slug>/<article_slug>/delete', methods=['GET', 'POST'])
# @auth.login_required
# def delete_article(world_slug, article_slug):
#     world = World.objects.get_or_404(slug=world_slug)
#     article = Article.objects.get_or_404(slug=article_slug)
#     if request.method == 'GET':
#         return article_server.render('delete', article, world=world)
#     elif request.method == 'POST':
#         return article_server.commit('delete', article, world=world)


