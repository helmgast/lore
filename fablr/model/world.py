"""
    model.world
    ~~~~~~~~~~~~~~~~

    Includes all game world related Mongoengine model classes, such as
    World, Article and so forth

    :copyright: (c) 2014 by Helmgast AB
"""

from fablr.app import db
from slugify import slugify
from user import User, Group
from asset import ImageAsset
import re
import logging
from misc import list_to_choices, Choices
from flask.ext.babel import lazy_gettext as _
import hashlib
from datetime import datetime
from time import strftime

import logging
from flask import current_app
logger = current_app.logger if current_app else logging.getLogger(__name__)

PublishStatus = Choices(
  draft=_('Draft'),
  revision=_('Revision'),
  published=_('Published'))

GenderTypes = Choices(
  male=_('Male'),
  female=_('Female'),
  unknown=_('Unknown'))

class World(db.Document):
  slug = db.StringField(unique=True, max_length=62) # URL-friendly name
  title = db.StringField(max_length=60)
  description = db.StringField(max_length=500)
  publisher = db.StringField(max_length=60)
  rule_system = db.StringField(max_length=60)
  created_date = db.DateTimeField(default=datetime.utcnow)

  def save(self, *args, **kwargs):
    self.slug = slugify(self.title)
    return super(World, self).save(*args, **kwargs)

  def __unicode__(self):
    return self.title+(_(' by ')+self.publisher) if self.publisher else ''

  def articles(self):
    return Article.objects(world=self)

  # startyear = 0
  # daysperyear = 360
  # datestring = "day %i in the year of %i"
  # calendar = [{name: january, days: 31}, {name: january, days: 31}, {name: january, days: 31}...]

class RelationType(db.Document):
  name = db.StringField() # human friendly name
  # code = CharField() # parent, child, reference,
  # display = CharField() # some display pattern to use for this relation, e.g. "%from is father to %to"
  # from_type = # type of article from
  # to_type = # type of article to

  def __str__(self):
    return unicode(self).encode('utf-8')

  def __unicode__(self):
    return u'%s' % self.name

class ArticleRelation(db.EmbeddedDocument):
  relation_type = db.ReferenceField(RelationType)
  article = db.ReferenceField('Article')

  def __str__(self):
    return unicode(self).encode('utf-8')

  def __unicode__(self):
    return u'%s %s %s' % (self.from_article.title, self.relation_type, self.to_article.title)

class PersonData(db.EmbeddedDocument):
  born = db.IntField(verbose_name = _('born'))
  died = db.IntField(verbose_name = _('died'))
  gender = db.StringField(default=GenderTypes.unknown, choices=GenderTypes.to_tuples(), verbose_name = _('gender'))
  # otherNames = CharField()
  occupation = db.StringField(max_length=60, verbose_name = _('occupation'))

  def gender_name(self):
    return GenderTypes[self.gender]

class FractionData(db.EmbeddedDocument):
  fraction_type = db.StringField(max_length=60, verbose_name = _('fraction'))

class PlaceData(db.EmbeddedDocument):
  # normalized position system, e.g. form 0 to 1 float, x and y
  coordinate_x = db.FloatField(verbose_name = _('Coordinate X'))
  coordinate_y = db.FloatField(verbose_name = _('Coordinate Y'))
  # building, city, domain, point_of_interest
  location_type = db.StringField(max_length=60, verbose_name = _('Location type'))

class EventData(db.EmbeddedDocument):
  from_date = db.IntField(verbose_name = _('From'))
  to_date = db.IntField(verbose_name = _('To'))

class Episode(db.EmbeddedDocument):
  id = db.StringField(unique=True) # URL-friendly name?
  title = db.StringField(max_length=60, verbose_name = _('Title'))
  description = db.StringField(verbose_name = _('Description'))
  content = db.ListField(db.ReferenceField('Article')) # references Article class below

# TODO: cannot add this to Episode as it's self reference, but adding attributes
# outside the class def seems not to be picked up by MongoEngine, so this row
# may not have any effect

class CampaignData(db.EmbeddedDocument):
  pass # TODO, the children her and above gives DuplicateIndices errors. Need to be fixed.

#  children = db.EmbeddedDocumentListField(Episode)

# class Tree(db.EmbeddedDocument):
#   pass

# class Branch(db.EmbeddedDocument):
#   subbranch = db.EmbeddedDocumentListField('self')
ArticleTypes = Choices(
  default=_('Default'),
  person=_('Person'),
  fraction=_('Fraction'),
  place=_('Place'),
  event=_('Event'),
  campaign=_('Campaign'),
  chronicles=_('Chronicle'),
  blogpost=_('Blog Post'))

# Those types that are actually EmbeddedDocuments. Other types may just be strings without metadata.
EMBEDDED_TYPES = ['persondata', 'fractiondata', 'placedata', 'eventdata', 'campaigndata']
class Article(db.Document):
  meta = {'indexes': ['slug']}
  slug = db.StringField(unique=True, required=False, max_length=62)
  type = db.StringField(choices=ArticleTypes.to_tuples(), default=ArticleTypes.default, verbose_name=_('Type'))
  world = db.ReferenceField(World, required=True, verbose_name=_('World'))
  creator = db.ReferenceField(User, verbose_name=_('Creator'))
  created_date = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Created on'))
  title = db.StringField(min_length=1, max_length=60, verbose_name=_('Title'))
  description = db.StringField(max_length=500, verbose_name=_('Description'))
  content = db.StringField()
  status = db.StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_('Status'))
  featured = db.BooleanField(default=False)
  feature_image = db.ReferenceField(ImageAsset)

  # modified_date = DateTimeField()

  # Changes type by nulling the old field, if it exists,
  # and creating an empty new one, if it exists.
  def change_type(self, new_type):
    if new_type != self.type and self.type is not None:  # may still be 0
      old_type_data = Article.type_data_name(self.type)
      if old_type_data in EMBEDDED_TYPES:
        # Null the old type
        setattr(self, old_type_data, None)
    if new_type is not None:  # may still be 0
      new_type_data = Article.type_data_name(new_type)
      if new_type_data in EMBEDDED_TYPES and getattr(self, new_type_data) is None:
        setattr(self, new_type_data, self._fields[new_type_data].document_type())

  # Executes before saving
  def clean(self):
    self.slug = slugify(self.title)

  def is_public(self):
    return self.is_published()

  def is_published(self):
    return self.status == PublishStatus.published and self.created_date <= datetime.utcnow()

  def status_name(self):
    return PublishStatus[self.status] + ( (' %s %s' % (_('from'), str(self.created_date))
        if self.status == PublishStatus.published and self.created_date >= datetime.utcnow() else '') )

  def type_name(self):
    return self.type if self.type != ArticleTypes.default else ''

  @staticmethod
  def type_data_name(asked_type):
    return asked_type + 'data'

  def __str__(self):
    return unicode(self).encode('utf-8')

  def __unicode__(self):
    return u'%s%s' % (self.title, ' [%s]' % self.type)

  persondata = db.EmbeddedDocumentField(PersonData)
  fractiondata = db.EmbeddedDocumentField(FractionData)
  placedata = db.EmbeddedDocumentField(PlaceData)
  eventdata = db.EmbeddedDocumentField(EventData)
  campaigndata = db.EmbeddedDocumentField(CampaignData)
  relations = db.ListField(db.EmbeddedDocumentField(ArticleRelation))

# ARTICLE_CREATOR, ARTICLE_EDITOR, ARTICLE_FOLLOWER = 0, 1, 2
# ARTICLE_USERS = ((ARTICLE_CREATOR, 'creator'), (ARTICLE_EDITOR,'editor'), (ARTICLE_FOLLOWER,'follower'))
# class ArticleUser(db.Document):
#     article = ForeignKeyField(Article, related_name='user')
#     user = ForeignKeyField(User)
#     type = IntegerField(default=ARTICLE_CREATOR, choices=ARTICLE_USERS)

# class ArticleGroup(db.Document):
#     article = db.ReferenceField(Article)
#     group = db.ReferenceField(Group)
#     type = db.IntField(choices=((GROUP_MASTER, 'master'), (GROUP_PLAYER, 'player')))

#     def __str__(self):
#         return unicode(self).encode('utf-8')

#     def __unicode__(self):
#         return u'%s (%ss)' % (self.group.name, GROUP_ROLE_TYPES[self.type])


# class ArticleRights(db.Document):
    # user = ForeignKeyField(User)
    # article = ForiegnKeyField(Article)
    # right = ForiegnKeyField(UserRights)
