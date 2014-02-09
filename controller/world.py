from flask import request, redirect, url_for, render_template, Blueprint, flash, make_response, g
from model.world import (Article, World, ArticleRelation, PersonArticle, PlaceArticle, 
  EventArticle, ImageArticle, FractionArticle, ARTICLE_DEFAULT, ARTICLE_IMAGE, 
  ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT, ARTICLE_TYPES)
from model.user import Group
from flask.views import View
from flask.ext.mongoengine.wtf import model_form, model_fields

from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter
from raconteur import auth, db
from itertools import groupby
from datetime import datetime, timedelta
from wtforms.fields import FieldList, HiddenField
from werkzeug.datastructures import ImmutableMultiDict

world_app = Blueprint('world', __name__, template_folder='templates/world')

world_handler = ResourceHandler(ResourceAccessStrategy(World, 'worlds', 'slug'))
world_handler.register_urls(world_app)

# field_dict = model_fields(Article, exclude=['slug'])
# for k in field_dict:
#   print k, field_dict[k], "\n"
# for f in Article._fields.keys():
#   print f
artform = model_form(Article, exclude=['slug'], converter=RacModelConverter())

article_handler = ResourceHandler(ResourceAccessStrategy(Article, 'articles', 'slug', 
    parent_strategy=world_handler.strategy, form_class = artform))
article_handler.register_urls(world_app)

article_relation_handler = ResourceHandler(ResourceAccessStrategy(ArticleRelation, 'relations', None,
  parent_strategy=article_handler.strategy))
article_relation_handler.register_urls(world_app)

@world_app.route('/')
def index():
    worlds = World.objects()
    return render_template('world/base.html', worlds=worlds)

@world_app.route('/image/<slug>')
def image(slug):
    imagearticle= Article.objects(slug=slug).first_or_404().imagearticle
    response = make_response(imagearticle.image.read())
    response.mimetype = imagearticle.mime_type
    return response

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