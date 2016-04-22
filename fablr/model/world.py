"""
    model.world
    ~~~~~~~~~~~~~~~~

    Includes all game world related Mongoengine model classes, such as
    World, Article and so forth

    :copyright: (c) 2014 by Helmgast AB
"""

import logging
from datetime import datetime, timedelta

from flask import current_app
from flask.ext.babel import lazy_gettext as _
from flask.ext.mongoengine import Document  # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, DateTimeField, FloatField, ReferenceField, BooleanField,
                         ListField, IntField, EmailField, EmbeddedDocumentField)

from asset import ImageAsset
from misc import Choices, slugify, Address, Languages, choice_options, datetime_options, reference_options
from user import User

logger = current_app.logger if current_app else logging.getLogger(__name__)

PublishStatus = Choices(
    draft=_('Draft'),
    revision=_('Revision'),
    published=_('Published'),
    archived=_('Archived'))

Licenses = Choices(
    public_domain=_('Public Domain'),
    all_rights_reserved=_('All Rights Reserved'),
    ccby4=_('Creative Commons Attribution 4.0'),
    ccbync4=_('Creative Commons Attribution + Non-commercial 4.0'))

GenderTypes = Choices(
    male=_('Male'),
    female=_('Female'),
    unknown=_('Unknown'))


class Publisher(Document):
    slug = StringField(unique=True, max_length=62)  # URL-friendly name
    short_code = StringField(min_length=2, max_length=2, verbose_name=_('Short Code'))
    title = StringField(min_length=3, max_length=60, verbose_name=_('Title'))
    description = StringField(max_length=500, verbose_name=_('Description'))
    created_date = DateTimeField(default=datetime.utcnow(), verbose_name=_('Created on'))
    owner = ReferenceField(User, verbose_name=_('Owner'))
    address = EmbeddedDocumentField(Address, verbose_name=_('Registered address'))
    email = EmailField(max_length=60, min_length=6, verbose_name=_('Email'))
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_('Status'))
    feature_image = ReferenceField(ImageAsset, verbose_name=_('Feature Image'))
    preferred_license = StringField(choices=Licenses.to_tuples(), default=Licenses.ccby4,
                                    verbose_name=_('Preferred License'))
    languages = ListField(StringField(choices=Languages.to_tuples(), verbose_name=_('Available Languages')))

    def __unicode__(self):
        return self.title


class World(Document):
    slug = StringField(unique=True, max_length=62)  # URL-friendly name
    title = StringField(min_length=3, max_length=60, verbose_name=_('Title'))
    description = StringField(max_length=500, verbose_name=_('Description'))
    publisher = ReferenceField(Publisher, verbose_name=_('Publisher'))  # TODO set to required
    creator = ReferenceField(User, verbose_name=_('Creator'))
    rule_system = StringField(max_length=60, verbose_name=_('Rule System'))
    created_date = DateTimeField(default=datetime.utcnow(), verbose_name=_('Created on'))
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_('Status'))
    feature_image = ReferenceField(ImageAsset, verbose_name=_('Feature Image'))
    preferred_license = StringField(choices=Licenses.to_tuples(), default=Licenses.ccby4,
                                    verbose_name=_('Preferred License'))
    languages = ListField(StringField(choices=Languages.to_tuples(), verbose_name=_('Available Languages')))

    def clean(self):
        self.slug = slugify(self.title)

    def __unicode__(self):
        return self.title

    def articles(self):
        return Article.objects(world=self).order_by('-created_date')

        # startyear = 0
        # daysperyear = 360
        # datestring = "day %i in the year of %i"
        # calendar = [{name: january, days: 31}, {name: january, days: 31}, {name: january, days: 31}...]


class WorldMeta(object):
    """This is a dummy World object that means no World, e.g. just articles with a Publisher"""
    slug = 'meta'
    languages = []

    def __init__(self, publisher):
        self.publisher = publisher

    def articles(self):
        return Article.objects(publisher=self.publisher, world=None).order_by('-created_date')


class RelationType(Document):
    name = StringField()  # human friendly name

    # code = CharField() # parent, child, reference,
    # display = CharField() # some display pattern to use for this relation, e.g. "%from is father to %to"
    # from_type = # type of article from
    # to_type = # type of article to

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s' % self.name


class ArticleRelation(EmbeddedDocument):
    relation_type = ReferenceField(RelationType)
    article = ReferenceField('Article')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s %s %s' % (self.from_article.title, self.relation_type, self.to_article.title)


class PersonData(EmbeddedDocument):
    born = IntField(verbose_name=_('born'))
    died = IntField(verbose_name=_('died'))
    gender = StringField(default=GenderTypes.unknown, choices=GenderTypes.to_tuples(), verbose_name=_('gender'))
    # otherNames = CharField()
    occupation = StringField(max_length=60, verbose_name=_('occupation'))

    def gender_name(self):
        return GenderTypes[self.gender]


class FractionData(EmbeddedDocument):
    fraction_type = StringField(max_length=60, verbose_name=_('fraction'))


class PlaceData(EmbeddedDocument):
    # normalized position system, e.g. form 0 to 1 float, x and y
    coordinate_x = FloatField(verbose_name=_('Coordinate X'))
    coordinate_y = FloatField(verbose_name=_('Coordinate Y'))
    # building, city, domain, point_of_interest
    location_type = StringField(max_length=60, verbose_name=_('Location type'))


class EventData(EmbeddedDocument):
    from_date = IntField(verbose_name=_('From'))
    to_date = IntField(verbose_name=_('To'))


class Episode(EmbeddedDocument):
    id = StringField(unique=True)  # URL-friendly name?
    title = StringField(max_length=60, verbose_name=_('Title'))
    description = StringField(verbose_name=_('Description'))
    content = ListField(ReferenceField('Article'))  # references Article class below


# TODO: cannot add this to Episode as it's self reference, but adding attributes
# outside the class def seems not to be picked up by MongoEngine, so this row
# may not have any effect

class CampaignData(EmbeddedDocument):
    pass  # TODO, the children her and above gives DuplicateIndices errors. Need to be fixed.


# children = EmbeddedDocumentListField(Episode)

# class Tree(EmbeddedDocument):
#   pass

# class Branch(EmbeddedDocument):
#   subbranch = EmbeddedDocumentListField('self')
ArticleTypes = Choices(
    default=_('Default'),
    blogpost=_('Blog Post'),
    material=_('Material'),
    person=_('Person'),
    fraction=_('Fraction'),
    place=_('Place'),
    event=_('Event'),
    campaign=_('Campaign'),
    chronicles=_('Chronicle')
)

ArticleThemes = Choices(
    default=_('Default'),
    newspaper=_('Newspaper'),
    inkletter=_('Ink Letter')
)

# Those types that are actually EmbeddedDocuments. Other types may just be strings without metadata.
EMBEDDED_TYPES = ['persondata', 'fractiondata', 'placedata', 'eventdata', 'campaigndata']


class Article(Document):
    meta = {'indexes': ['slug']}
    slug = StringField(unique=True, required=False, max_length=62)
    type = StringField(choices=ArticleTypes.to_tuples(), default=ArticleTypes.default, verbose_name=_('Type'))
    world = ReferenceField(World, verbose_name=_('World'))
    publisher = ReferenceField(Publisher, verbose_name=_('Publisher'))
    creator = ReferenceField(User, verbose_name=_('Creator'))
    created_date = DateTimeField(default=datetime.utcnow(), verbose_name=_('Created on'))
    title = StringField(min_length=1, max_length=60, verbose_name=_('Title'))
    description = StringField(max_length=500, verbose_name=_('Description'))
    content = StringField(verbose_name=_('Content'))
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_('Status'))
    featured = BooleanField(default=False, verbose_name=_('Featured article'))
    feature_image = ReferenceField(ImageAsset, verbose_name=_('Feature Image'))
    license = StringField(choices=Licenses.to_tuples(), default=Licenses.ccby4, verbose_name=_('License'))
    theme = StringField(choices=ArticleThemes.to_tuples(),
                        default=ArticleThemes.default,
                        verbose_name=_('Article Theme'))
    editors = ListField(ReferenceField(User), verbose_name=_('Editors'))
    readers = ListField(ReferenceField(User), verbose_name=_('Readers'))

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
        return PublishStatus[self.status] + ((' %s %s' % (_('from'), str(self.created_date))
                                              if self.status == PublishStatus.published and self.created_date >= datetime.utcnow() else ''))

    @staticmethod
    def type_data_name(asked_type):
        return asked_type + 'data'

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s%s' % (self.title, ' [%s]' % self.type)

    persondata = EmbeddedDocumentField(PersonData)
    fractiondata = EmbeddedDocumentField(FractionData)
    placedata = EmbeddedDocumentField(PlaceData)
    eventdata = EmbeddedDocumentField(EventData)
    campaigndata = EmbeddedDocumentField(CampaignData)
    relations = ListField(EmbeddedDocumentField(ArticleRelation))


Article.type.filter_options = choice_options('type', Article.type.choices)
Article.world.filter_options = reference_options('world', Article)
Article.created_date.filter_options = datetime_options('created_date',
                                                       [timedelta(days=7),
                                                        timedelta(days=30),
                                                        timedelta(days=90),
                                                        timedelta(days=365)])

# ARTICLE_CREATOR, ARTICLE_EDITOR, ARTICLE_FOLLOWER = 0, 1, 2
# ARTICLE_USERS = ((ARTICLE_CREATOR, 'creator'), (ARTICLE_EDITOR,'editor'), (ARTICLE_FOLLOWER,'follower'))
# class ArticleUser(Document):
#     article = ForeignKeyField(Article, related_name='user')
#     user = ForeignKeyField(User)
#     type = IntegerField(default=ARTICLE_CREATOR, choices=ARTICLE_USERS)

# class ArticleGroup(Document):
#     article = ReferenceField(Article)
#     group = ReferenceField(Group)
#     type = IntField(choices=((GROUP_MASTER, 'master'), (GROUP_PLAYER, 'player')))

#     def __str__(self):
#         return unicode(self).encode('utf-8')

#     def __unicode__(self):
#         return u'%s (%ss)' % (self.group.name, GROUP_ROLE_TYPES[self.type])


# class ArticleRights(Document):
# user = ForeignKeyField(User)
# article = ForeignKeyField(Article)
# right = ForeignKeyField(UserRights)
