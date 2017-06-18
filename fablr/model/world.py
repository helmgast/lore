"""
    model.world
    ~~~~~~~~~~~~~~~~

    Includes all game world related Mongoengine model classes, such as
    World, Article and so forth

    :copyright: (c) 2014 by Helmgast AB
"""

import logging
import re
from datetime import datetime, timedelta

from flask import current_app
from flask_babel import lazy_gettext as _
from misc import Document, available_locale_tuples, distinct_options  # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, DateTimeField, FloatField, ReferenceField, BooleanField,
                         ListField, IntField, EmailField, EmbeddedDocumentField, DictField,
                         GenericEmbeddedDocumentField, DynamicEmbeddedDocument, DynamicField, URLField, NULLIFY, DENY, CASCADE)

from asset import FileAsset
from misc import Choices, slugify, Address, choice_options, datetime_delta_options, reference_options
from user import User

logger = current_app.logger if current_app else logging.getLogger(__name__)

PublishStatus = Choices(
    draft=_('Draft'),  # not published, visible to owner and editors
    revision=_('Revision'),  # an older revision of the same article, currently not in use
    published=_('Published'),  # published to all with normal access rights (ignoring "readers" attribute")
    private=_('Private'),  # published, but only visible to those with explicit access
    archived=_('Archived'))  # passed publishing, visible to owners and editors but not others

Licenses = Choices(
    public_domain=_('Public Domain'),
    all_rights_reserved=_('All Rights Reserved'),
    ccby4=_('Creative Commons Attribution 4.0'),
    ccbync4=_('Creative Commons Attribution + Non-commercial 4.0'))

GenderTypes = Choices(
    male=_('Male'),
    female=_('Female'),
    unknown=_('Unknown'))


def secure_css(css):
    css = re.sub(r'<.*', '', css, flags=re.IGNORECASE)
    css = re.sub(r'expression\(', '', css, flags=re.IGNORECASE)
    css = re.sub(r'javascript:', '', css, flags=re.IGNORECASE)
    css = re.sub(r'\.htc:', '', css, flags=re.IGNORECASE)
    return css


class Publisher(Document):
    slug = StringField(unique=True, max_length=62, verbose_name=_('Publisher Domain'))  # URL-friendly name
    publisher_code = StringField(min_length=2, max_length=2, verbose_name=_('Publisher Code'))
    title = StringField(min_length=3, max_length=60, required=True, verbose_name=_('Title'))
    tagline = StringField(min_length=0, max_length=100, verbose_name=_('Tagline'))
    description = StringField(max_length=350, verbose_name=_('Description'))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_('Created on'))
    creator = ReferenceField(User, reverse_delete_rule=NULLIFY, verbose_name=_('Owner'))
    address = EmbeddedDocumentField(Address, verbose_name=_('Registered address'))
    email = EmailField(max_length=60, min_length=6, verbose_name=_('Email'))
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_('Status'))
    contribution = BooleanField(default=False, verbose_name=_('Publisher accepts contributions'))

    # TODO DEPRECATE in DB version 3
    feature_image = ReferenceField(FileAsset, reverse_delete_rule=NULLIFY, verbose_name=_('Feature Image'))
    images = ListField(ReferenceField(FileAsset, reverse_delete_rule=NULLIFY), verbose_name=_('Publisher Images'))

    webshop_url = URLField(verbose_name=_('Webshop URL'))
    facebook_url = URLField(verbose_name=_('Facebook URL'))
    webshop_activated = BooleanField(default=False, verbose_name=_('Activate webshop'))

    editors = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_('Editors'))
    readers = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_('Readers'))

    # Settings per publisher
    languages = ListField(StringField(choices=available_locale_tuples), verbose_name=_('Available Languages'))
    preferred_license = StringField(choices=Licenses.to_tuples(), default=Licenses.ccby4,
                                    verbose_name=_('Preferred License'))

    def worlds(self):
        return World.objects(publisher=self).order_by('-created_date')

    def is_published(self):
        return self.status == PublishStatus.published and self.created_date <= datetime.utcnow()

    def __str__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return self.title or self.slug

# Regsister delete rule here becaue in User, we haven't imported Publisher so won't work from there
Publisher.register_delete_rule(User, 'publishers_newsletters', NULLIFY)

class World(Document):
    slug = StringField(unique=True, max_length=62)  # URL-friendly name
    title = StringField(min_length=3, max_length=60, required=True, verbose_name=_('Title'))
    description = StringField(max_length=350, verbose_name=_('Description'))
    content = StringField(verbose_name=_('Content'))
    tagline = StringField(min_length=0, max_length=100, verbose_name=_('Tagline'))
    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, verbose_name=_('Publisher'))  # TODO set to required
    creator = ReferenceField(User, reverse_delete_rule=NULLIFY, verbose_name=_('Creator'))
    rule_system = StringField(max_length=60, verbose_name=_('Rule System'))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_('Created on'))
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_('Status'))
    contribution = BooleanField(default=False, verbose_name=_('World accepts contributions'))
    external_host = URLField(verbose_name=_('External host URL'))
    publishing_year = StringField(max_length=4, verbose_name=_('Publishing year'))

    # TODO DEPRECATE in DB version 3
    feature_image = ReferenceField(FileAsset, verbose_name=_('Feature Image'))
    images = ListField(ReferenceField(FileAsset, reverse_delete_rule=NULLIFY), verbose_name=_('World Images'))
    product_url = URLField(verbose_name=_('Product URL'))
    facebook_url = URLField(verbose_name=_('Facebook URL'))

    preferred_license = StringField(choices=Licenses.to_tuples(), default=Licenses.ccby4,
                                    verbose_name=_('Preferred License'))
    languages = ListField(StringField(choices=available_locale_tuples), verbose_name=_('Available Languages'))
    editors = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_('Editors'))
    readers = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_('Readers'))

    custom_css = StringField(verbose_name=_('Custom CSS'))


    def clean(self):
        self.title = self.title.replace(u'&shy;', u'\u00AD')  # Replaces soft hyphens with the real unicode
        self.slug = slugify(self.title)
        if self.creator and self.creator not in self.editors:
            self.editors.append(self.creator)
        self.custom_css = secure_css(self.custom_css)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.title

    def articles(self):
        return Article.objects(world=self).order_by('-created_date')

    def is_published(self):
        return self.status == PublishStatus.published and self.created_date <= datetime.utcnow()

    @property  # For convenience
    def get_feature_image(self):
        # Smallest aspect
        newlist = sorted(self.images, key=lambda x: x.aspect_ratio())
        return newlist[0] if newlist else None

    @property  # For convenience
    def get_header_image(self):
        # Largest aspect
        newlist = sorted(self.images, key=lambda x: x.aspect_ratio(), reverse=True)
        return newlist[0] if newlist and newlist[0].aspect_ratio() > 1 else None

        # startyear = 0
        # daysperyear = 360
        # datestring = "day %i in the year of %i"
        # calendar = [{name: january, days: 31}, {name: january, days: 31}, {name: january, days: 31}...]

# Regsister delete rule here becaue in User, we haven't imported Publisher so won't work from there
Publisher.register_delete_rule(User, 'world_newsletters', NULLIFY)

class WorldMeta(object):
    """This is a dummy World object that means no World, e.g. just articles with a Publisher"""
    slug = 'meta'
    languages = []
    editors = []
    title = ''
    creator = None

    def __init__(self, publisher):
        self.publisher = publisher
        self.title = publisher.title

    def __unicode__(self):
        return unicode(self.publisher) or u'Meta'

    def __nonzero__(self):
        return False  # Behave as false

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
    born = IntField(verbose_name=_('Born'))
    died = IntField(verbose_name=_('Died'))
    gender = StringField(default=GenderTypes.unknown, choices=GenderTypes.to_tuples(), verbose_name=_('Gender'))
    # otherNames = CharField()
    occupation = StringField(max_length=60, verbose_name=_('Occupation'))

    def gender_name(self):
        return GenderTypes[self.gender]


class FractionData(EmbeddedDocument):
    fraction_type = StringField(max_length=60, verbose_name=_('Fraction'))


class PlaceData(EmbeddedDocument):
    # normalized position system, e.g. form 0 to 1 float, x and y
    coordinate_x = FloatField(verbose_name=_('Coordinate X'))
    coordinate_y = FloatField(verbose_name=_('Coordinate Y'))
    # building, city, domain, point_of_interest
    location_type = StringField(max_length=60, verbose_name=_('Location type'))


class EventData(EmbeddedDocument):
    from_date = IntField(verbose_name=_('From'))
    to_date = IntField(verbose_name=_('To'))


class CharacterData(EmbeddedDocument):
    stats = DynamicField()


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
    chronicles=_('Chronicle'),
    character=_('Character')
)

ArticleThemes = Choices(
    default=_('Default'),
    newspaper=_('Newspaper'),
    inkletter=_('Ink Letter'),
    papernote=_('Paper Note'),
    vintage_form=_('Vintage Form'),
)

# Those types that are actually EmbeddedDocuments. Other types may just be strings without metadata.
EMBEDDED_TYPES = ['persondata', 'fractiondata', 'placedata', 'eventdata', 'campaigndata', 'characterdata']


class Article(Document):
    meta = {
        'indexes': [
            'slug',
            {'fields': ['$title', "$content", "$tags"]}
        ],
        # 'auto_create_index': True
    }
    slug = StringField(unique=True, required=False, max_length=62)
    type = StringField(choices=ArticleTypes.to_tuples(), default=ArticleTypes.default, verbose_name=_('Type'))
    world = ReferenceField(World, reverse_delete_rule=DENY, verbose_name=_('World'))
    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, verbose_name=_('Publisher'))
    creator = ReferenceField(User, verbose_name=_('Creator'))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
    title = StringField(min_length=1, max_length=60, required=True, verbose_name=_('Title'))
    description = StringField(max_length=350, verbose_name=_('Description'))
    content = StringField(verbose_name=_('Content'))
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_('Status'))
    tags = ListField(StringField(max_length=30), verbose_name=_('Tags'))

    # Sort higher numbers first, lower later. Top 5 highest numbers used to
    sort_priority = IntField(default=0, verbose_name=_('Sort priority'))

    # TODO DEPRECATE in DB version 3
    featured = BooleanField(default=False, verbose_name=_('Featured article'))
    feature_image = ReferenceField(FileAsset, reverse_delete_rule=NULLIFY, verbose_name=_('Feature Image'))

    images = ListField(ReferenceField(FileAsset, reverse_delete_rule=NULLIFY), verbose_name=_('Images'))
    license = StringField(choices=Licenses.to_tuples(), default=Licenses.ccby4, verbose_name=_('License'))
    theme = StringField(choices=ArticleThemes.to_tuples(),
                        default=ArticleThemes.default,
                        verbose_name=_('Theme'))
    editors = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_('Editors'))
    readers = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_('Readers'))
    custom_css = StringField(verbose_name=_('Custom CSS'))

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

    def long_title(self):
        return u"%s - %s" % (self.world or self.world or u'Fablr', self)

    @property  # For convenience
    def get_feature_image(self):
        # Smallest aspect
        newlist = sorted(self.images, key=lambda x: x.aspect_ratio())
        return newlist[0] if newlist else None

    @property  # For convenience
    def get_header_image(self):
        # Largest aspect
        newlist = sorted(self.images, key=lambda x: x.aspect_ratio(), reverse=True)
        return newlist[0] if newlist and newlist[0].aspect_ratio() > 1 else None

    # Executes before saving
    def clean(self):
        self.title = self.title.replace(u'&shy;', u'\u00AD')  # Replaces soft hyphens with the real unicode
        self.slug = slugify(self.title)
        if self.creator and self.creator not in self.editors:
            self.editors.append(self.creator)

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
    characterdata = EmbeddedDocumentField(CharacterData)

    relations = ListField(EmbeddedDocumentField(ArticleRelation))


Article.type.filter_options = choice_options('type', Article.type.choices)
Article.status.filter_options = choice_options('status', Article.status.choices)
Article.world.filter_options = reference_options('world', Article)
Article.tags.filter_options = distinct_options('tags', Article)
Article.created_date.filter_options = datetime_delta_options('created_date',
                                                             [timedelta(days=7),
                                                              timedelta(days=30),
                                                              timedelta(days=90),
                                                              timedelta(days=365)])


class Shortcut(Document):
    long_url = URLField(verbose_name=_('Long URL'))
    slug = StringField(unique=True, required=True, max_length=10, verbose_name=_('Slug'))
    description = StringField(max_length=500, verbose_name=_('Description'))
    hits = IntField(min_value=0, verbose_name=_('Hits'))

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
