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
ARTICLE_DEFAULT, ARTICLE_IMAGE, ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT, ARTICLE_CAMPAIGN, ARTICLE_CHRONICLE, ARTICLE_BLOG = 0, 1, 2, 3, 4, 5, 6, 7, 8
ARTICLE_TYPES = ((ARTICLE_DEFAULT, _('default')),
                 (ARTICLE_IMAGE, _('image')),
                 (ARTICLE_PERSON, _('person')),
                 (ARTICLE_FRACTION, _('fraction')),
                 (ARTICLE_PLACE, _('place')),
                 (ARTICLE_EVENT, _('event')),
                 (ARTICLE_CAMPAIGN, _('campaign')),
                 (ARTICLE_CHRONICLE, _('chronicle')),
                 (ARTICLE_BLOG, _('blogpost')))


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

class ImageArticle(db.EmbeddedDocument):
    image = db.ImageField()
    source_image_url = db.URLField()
    source_page_url = db.URLField()
    # TODO MongoEngine should allow a simple tuple for choices, not having to add JPEG, PNG and GIF fields
    mime_type = db.StringField(choices=(('image/jpeg','JPEG'),('image/png','PNG'), ('image/gif','GIF')), required=True)

    @classmethod
    def create_from_url(cls, image_url, source_url=None):
        r = requests.get(image_url)
        im = ImageArticle(source_image_url=image_url, source_page_url=source_url)
        im.image.put(StringIO(r.content))
        im.mime_type = 'image/'+im.image.format.lower()
        # TODO very poor way of correctly determining mime type
        # TODO use md5 to check if file already downloaded
        logger = logging.getLogger(__name__)
        logger.info("Fetched %s image from %s to DB", im.image.format, image_url)
        return im

class PersonArticle(db.EmbeddedDocument):
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

class FractionArticle(db.EmbeddedDocument):
    fraction_type = db.StringField(max_length=60)
    #i18n
    fraction_type.verbose_name = _('fraction')

class PlaceArticle(db.EmbeddedDocument):
    # normalized position system, e.g. form 0 to 1 float, x and y
    coordinate_x = db.FloatField()
    coordinate_y = db.FloatField()
    # building, city, domain, point_of_interest
    location_type = db.StringField(max_length=60)
    #i18n
    coordinate_x.verbose_name = _('Coordinate X')
    coordinate_y.verbose_name = _('Coordinate Y')
    location_type.verbose_name = _('Location type')

class EventArticle(db.EmbeddedDocument):
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

class CampaignArticle(db.EmbeddedDocument):
    children = db.ListField(db.EmbeddedDocumentField(Episode))

# Those types that are actually EmbeddedDocuments. Other types may just be strings without metadata.
EMBEDDED_TYPES = ['imagearticle','personarticle','fractionarticle','placearticle', 'eventarticle', 'campaignarticle']
class Article(db.Document):
    meta = {'indexes': ['slug']}
    slug = db.StringField(unique=True, required=False, max_length=62) # URL-friendly name, removed "unique", slug cannot be guaranteed to be unique
    type = db.IntField(choices=ARTICLE_TYPES, default=ARTICLE_DEFAULT, verbose_name=_('Type'))
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
            type_name = self.type_name()+'article'
            if type_name in EMBEDDED_TYPES:
                # Null the old type
                setattr(self, type_name, None)
        if new_type is not None: # may still be 0
            type_name = Article.create_type_name(new_type)+'article'
            if type_name in EMBEDDED_TYPES and getattr(self, type_name) is None:
                setattr(self, type_name, self._fields[type_name].document_type())

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super(Article, self).save(*args, **kwargs)

    def is_person(self):
        return ARTICLE_PERSON == self.type

    def is_image(self):
        return ARTICLE_IMAGE == self.type

    def type_name(self):
        return Article.create_type_name(self.type)

    @staticmethod
    def create_type_name(asked_type):
        return ARTICLE_TYPES[asked_type][1]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s%s' % (self.title, ' [%s]' % self.type_name() if self.type > 0 else '')

    imagearticle = db.EmbeddedDocumentField(ImageArticle)
    personarticle = db.EmbeddedDocumentField(PersonArticle)
    fractionarticle = db.EmbeddedDocumentField(FractionArticle)
    placearticle = db.EmbeddedDocumentField(PlaceArticle)
    eventarticle = db.EmbeddedDocumentField(EventArticle)
    campaignarticle = db.EmbeddedDocumentField(CampaignArticle)

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