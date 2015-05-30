"""
    model.world
    ~~~~~~~~~~~~~~~~

    Includes all game world related Mongoengine model classes, such as
    World, Article and so forth

    :copyright: (c) 2014 by Raconteur
"""

from raconteur import db
from slugify import slugify
from user import User, Group
import requests
from StringIO import StringIO
import re
import logging
import imghdr
from misc import list_to_choices, Choices
from flask.ext.babel import lazy_gettext as _
import hashlib
from werkzeug.utils import secure_filename
from mongoengine.queryset import Q
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

MimeTypes = Choices({
  'image/jpeg': 'JPEG',
  'image/png':'PNG',
  'image/gif':'GIF'
  })
IMAGE_FILE_ENDING = {'image/jpeg':'jpg','image/png':'png','image/gif':'gif'}
class ImageAsset(db.Document):
  slug = db.StringField(primary_key=True, min_length=5, max_length=60, verbose_name=_('Slug'))
  meta = {'indexes': ['slug']}
  image = db.ImageField(thumbnail_size=(300,300,False), required=True)
  source_image_url = db.URLField()
  source_page_url = db.URLField()
  tags = db.ListField(db.StringField(max_length=30))
  mime_type = db.StringField(choices=MimeTypes.to_tuples(), required=True)
  creator = db.ReferenceField(User, verbose_name=_('Creator'))
  created_date = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Created date'))
  title = db.StringField(min_length=1, max_length=60, verbose_name=_('Title'))
  description = db.StringField(max_length=500, verbose_name=_('Description'))

  def __unicode__(self):
    return u'%s' % self.slug

  # Executes before saving
  def clean(self):
    if self.title:
      slug, end = secure_filename(self.title).rsplit('.', 1)
      if len(end)>4:
        slug = slug+end # end is probably not a file ending
    else:
      slug = self.id
    if not slug:
      raise ValueError('Cannot make slug from either title %s or id %s' % (self.title, self.id))
    new_end = IMAGE_FILE_ENDING[self.mime_type]
    new_slug = slug+'.'+new_end
    existing = len(ImageAsset.objects(Q(slug__endswith='__'+new_slug) or Q(slug=new_slug)))
    if existing:
      new_slug = "%i__%s.%s" % (existing+1, slug, new_end)
    self.slug = new_slug

  def make_from_url(self, image_url, source_url=None):
    # TODO use md5 to check if file already downloaded
    file = StringIO(requests.get(image_url).content)
    self.make_from_file(file)
    self.source_image_url = image_url
    self.source_page_url = source_url
    self.title = self.title or image_url.rsplit('/',1)[-1]
    logger.info("Fetched %s image from %s to DB", self.image.format, image_url)

  def make_from_file(self, file):
    # block_size=256*128
    # md5 = hashlib.md5()
    # for chunk in iter(lambda: file.read(block_size), b''):
    #      md5.update(chunk)
    # print md5.hexdigest()
    # file.seek(0) # reset
    self.image.put(file)
    self.mime_type = 'image/%s' % self.image.format.lower()

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
Episode.children = db.ListField(db.EmbeddedDocumentField(Episode)) # references Episode class

class CampaignData(db.EmbeddedDocument):
  children = db.ListField(db.EmbeddedDocumentField(Episode))

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
  status = db.StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.draft, verbose_name=_('Status'))
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
