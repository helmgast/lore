"""
    model.world
    ~~~~~~~~~~~~~~~~

    Includes all game world related Mongoengine model classes, such as
    World, Article and so forth

    :copyright: (c) 2014 by Raconteur
"""

from raconteur import db
from misc import now
from slugify import slugify
from user import User, Group
import requests
from StringIO import StringIO
import re
import logging
from flask.ext.babel import lazy_gettext as _

# Constants and enumerations

def list_to_choices(list):
    return [(s, _(s)) for s in list]

PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_REVISION, PUBLISH_STATUS_PUBLISHED = 0, 1, 2
PUBLISH_STATUS_TYPES = ((PUBLISH_STATUS_DRAFT, _('draft')),
                        (PUBLISH_STATUS_REVISION, _('revision')),
                        (PUBLISH_STATUS_PUBLISHED, _('published')))

GENDER_UNKNOWN, GENDER_MALE, GENDER_FEMALE = 0, 1, 2
GENDER_TYPES = ((GENDER_UNKNOWN, _('unknown')),
                (GENDER_MALE, _('male')),
                (GENDER_FEMALE, _('female')))

class World(db.Document):
    slug = db.StringField(unique=True, max_length=62) # URL-friendly name
    title = db.StringField(max_length=60)
    description = db.StringField(max_length=500)
    publisher = db.StringField(max_length=60)
    rule_system = db.StringField(max_length=60)
    created_date = db.DateTimeField(default=now)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super(World, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title+(' by '+self.publisher) if self.publisher else ''

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
#    article = db.ReferenceField(Article)
    relation_type = db.ReferenceField(RelationType)
    article = db.ReferenceField('Article')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s %s %s' % (self.from_article.title, self.relation_type, self.to_article.title)

class ImageData(db.EmbeddedDocument):
    image = db.ImageField()
    source_image_url = db.URLField()
    source_page_url = db.URLField()
    # TODO MongoEngine should allow a simple tuple for choices, not having to add JPEG, PNG and GIF fields
    mime_type = db.StringField(choices=(('image/jpeg','JPEG'),('image/png','PNG'), ('image/gif','GIF')), required=True)

    @classmethod
    def create_from_url(cls, image_url, source_url=None):
        r = requests.get(image_url)
        im = ImageData(source_image_url=image_url, source_page_url=source_url)
        im.image.put(StringIO(r.content))
        im.mime_type = 'image/'+im.image.format.lower()
        # TODO very poor way of correctly determining mime type
        # TODO use md5 to check if file already downloaded
        logger = logging.getLogger(__name__)
        logger.info("Fetched %s image from %s to DB", im.image.format, image_url)
        return im

class PersonData(db.EmbeddedDocument):
    born = db.IntField()
    died = db.IntField()
    gender = db.IntField(default=GENDER_UNKNOWN, choices=GENDER_TYPES)
    # otherNames = CharField()
    occupation = db.StringField(max_length=60)

    #i18n things
    born.verbose_name = _('born')
    died.verbose_name = _('died')
    gender.verbose_name = _('gender')
    occupation.verbose_name = _('occupation')

    def gender_name(self):
        return GENDER_TYPES[self.gender][1].title()

class FractionData(db.EmbeddedDocument):
    fraction_type = db.StringField(max_length=60)
    #i18n
    fraction_type.verbose_name = _('fraction')

class PlaceData(db.EmbeddedDocument):
    # normalized position system, e.g. form 0 to 1 float, x and y
    coordinate_x = db.FloatField()
    coordinate_y = db.FloatField()
    # building, city, domain, point_of_interest
    location_type = db.StringField(max_length=60)
    #i18n
    coordinate_x.verbose_name = _('Coordinate X')
    coordinate_y.verbose_name = _('Coordinate Y')
    location_type.verbose_name = _('Location type')

class EventData(db.EmbeddedDocument):
    from_date = db.IntField()
    to_date = db.IntField()

    from_date.verbose_name = _('From')
    to_date.verbose_name = _('To')

class Episode(db.EmbeddedDocument):
    id = db.StringField(unique=True) # URL-friendly name?
    title = db.StringField(max_length=60)
    description = db.StringField()
    content = db.ListField(db.ReferenceField('Article')) # references Article class below

    #i18n
    title.verbose_name = _('Title')
    description.verbose_name = _('Description')

# TODO: cannot add this to Episode as it's self reference, but adding attributes
# outside the class def seems not to be picked up by MongoEngine, so this row
# may not have any effect
Episode.children = db.ListField(db.EmbeddedDocumentField(Episode)) # references Episode class

class CampaignData(db.EmbeddedDocument):
    children = db.ListField(db.EmbeddedDocumentField(Episode))

ARTICLE_TYPES = list_to_choices([
    'default', 
    'image',
    'person',
    'fraction',
    'place',
    'event',
    'campaign',
    'chronicle',
    'blogpost'
    ])

# Those types that are actually EmbeddedDocuments. Other types may just be strings without metadata.
EMBEDDED_TYPES = ['imagedata','persondata','fractiondata','placedata', 'eventdata', 'campaigndata']
class Article(db.Document):
    meta = {'indexes': ['slug']}
    slug = db.StringField(unique=True, required=False, max_length=62) # URL-friendly name, removed "unique", slug cannot be guaranteed to be unique
    type = db.StringField(choices=ARTICLE_TYPES, default='default', verbose_name=_('Type'))
    world = db.ReferenceField(World, verbose_name=_('World'))
    creator = db.ReferenceField(User, verbose_name=_('Creator'))
    created_date = db.DateTimeField(default=now)
    title = db.StringField(min_length=1, max_length=60, verbose_name=_('Title'))
    description = db.StringField(max_length=500, verbose_name=_('Description'))
    content = db.StringField()
    status = db.IntField(choices=PUBLISH_STATUS_TYPES, default=PUBLISH_STATUS_DRAFT, verbose_name=_('Status'))

    # modified_date = DateTimeField()

    # Changes type by nulling the old field, if it exists,
    # and creating an empty new one, if it exists.
    def change_type(self, new_type):
        if new_type!=self.type and self.type is not None: # may still be 0
            old_type_data = Article.type_data_name(self.type)
            if old_type_data in EMBEDDED_TYPES:
                # Null the old type
                setattr(self, type_data, None)
        if new_type is not None: # may still be 0
            new_type_data = Article.type_data_name(new_type)
            if new_type_data in EMBEDDED_TYPES and getattr(self, new_type_data) is None:
                setattr(self, new_type_data, self._fields[new_type_data].document_type())

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super(Article, self).save(*args, **kwargs)

    @staticmethod
    def type_data_name(asked_type):
        return asked_type+'data'

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s%s' % (self.title, ' [%s]' % self.type)

    imagedata = db.EmbeddedDocumentField(ImageData)
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