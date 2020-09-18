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

from flask import current_app, g, url_for
from flask_babel import lazy_gettext as _
from mongoengine import (
    DENY,
    NULLIFY,
    BooleanField,
    DateTimeField,
    DynamicField,
    EmailField,
    EmbeddedDocument,
    EmbeddedDocumentField,
    FloatField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
    URLField,
)
from mongoengine.fields import MapField
from mongoengine.queryset import Q

from .asset import Attachment, FileAsset
from .misc import (
    EMPTY_ID,
    Address,
    Choices,
    Document,  # Enhanced document
    choice_options,
    configured_langs_tuples,
    datetime_delta_options,
    distinct_options,
    get,
    pick_i18n,
    reference_options,
    shorten,
    slugify,
)
from lore.extensions import configured_langs, default_locale
from .user import User, user_from_email

logger = current_app.logger if current_app else logging.getLogger(__name__)

PublishStatus = Choices(
    draft=_("Draft"),  # not published, visible to owner and editors
    revision=_("Revision"),  # an older revision of the same article, currently not in use
    published=_("Published"),  # published to all with normal access rights (ignoring "readers" attribute")
    private=_("Private"),  # published, but only visible to those with explicit access
    archived=_("Archived"),
)  # passed publishing, visible to owners and editors but not others

Licenses = Choices(
    public_domain=_("Public Domain"),
    all_rights_reserved=_("All Rights Reserved"),
    ccby4=_("Creative Commons Attribution 4.0"),
    ccbync4=_("Creative Commons Attribution + Non-commercial 4.0"),
)

GenderTypes = Choices(male=_("Male"), female=_("Female"), unknown=_("Unknown"))


# Generate the choices at runtime instead of import time
plugin_choices = []


def secure_css(css):
    if css:
        css = re.sub(r"<.*", "", css, flags=re.IGNORECASE)
        css = re.sub(r"expression\(", "", css, flags=re.IGNORECASE)
        css = re.sub(r"javascript:", "", css, flags=re.IGNORECASE)
        css = re.sub(r"\.htc:", "", css, flags=re.IGNORECASE)
    return css


class Publisher(Document):
    meta = {"strict": False}

    slug = StringField(unique=True, max_length=62, verbose_name=_("Publisher Domain"))  # URL-friendly name
    publisher_code = StringField(min_length=2, max_length=2, verbose_name=_("Publisher Code"))
    title = StringField(min_length=3, max_length=60, required=True, verbose_name=_("Title"))

    tagline_i18n = MapField(StringField(min_length=0, max_length=100), verbose_name=_("Tagline"))

    description = StringField(max_length=350, verbose_name=_("Description"))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_("Created on"))
    creator = ReferenceField(User, reverse_delete_rule=NULLIFY, verbose_name=_("Owner"))
    address = EmbeddedDocumentField(Address, verbose_name=_("Registered address"))
    email = EmailField(max_length=60, min_length=6, verbose_name=_("Email"))
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_("Status"))
    contribution = BooleanField(default=False, verbose_name=_("Publisher accepts contributions"))
    theme = StringField(choices=plugin_choices, null=True, verbose_name=_("Theme"))

    # TODO DEPRECATE in DB version 3
    feature_image = ReferenceField(FileAsset, reverse_delete_rule=NULLIFY, verbose_name=_("Feature Image"))
    images = ListField(ReferenceField(FileAsset, reverse_delete_rule=NULLIFY), verbose_name=_("Publisher Images"))

    webshop_url = URLField(verbose_name=_("Webshop URL"))
    facebook_url = URLField(verbose_name=_("Facebook URL"))
    webshop_activated = BooleanField(default=False, verbose_name=_("Activate webshop"))

    editors = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_("Editors"))
    readers = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_("Readers"))

    # Settings per publisher
    languages = ListField(StringField(choices=configured_langs_tuples), verbose_name=_("Available Languages"))
    preferred_license = StringField(
        choices=Licenses.to_tuples(), default=Licenses.ccby4, verbose_name=_("Preferred License")
    )

    @property  # For convenience
    def tagline(self):
        return pick_i18n(self.tagline_i18n)

    @tagline.setter
    def set_tagline(self):
        raise NotImplementedError()

    def worlds(self):
        return World.objects(publisher=self).order_by("-created_date")

    def is_published(self):
        return self.status == PublishStatus.published and self.created_date <= datetime.utcnow()

    def __str__(self):
        return self.title or self.slug


# Regsister delete rule here becaue in User, we haven't imported Publisher so won't work from there
Publisher.register_delete_rule(User, "publishers_newsletters", NULLIFY)


def filter_authorized_by_publisher(publisher=None):
    if not g.user:
        return Q(id=EMPTY_ID)
    if not publisher:
        # Check all publishers
        return Q(publisher__in=Publisher.objects(Q(editors__all=[g.user]) | Q(readers__all=[g.user])))
    elif g.user in publisher.editors or g.user in publisher.readers:
        # Save some time and only check given publisher
        return Q(publisher__in=[publisher])
    else:
        return Q(id=EMPTY_ID)


class World(Document):
    meta = {"strict": False}
    # db.getCollection('world').update(
    #   {},
    #   { $rename: { "title": "title_i18n.sv",  "description": "description_i18n.sv", "tagline": "tagline_i18n.sv", "content": "content_i18n.sv"} } ,
    #   {multi:true})

    slug = StringField(unique=True, max_length=62)  # URL-friendly name
    # TODO should have required and min_length, but fails with our MapField implementation
    title_i18n = MapField(StringField(max_length=60), verbose_name=_("Title"),)
    description_i18n = MapField(StringField(max_length=350), verbose_name=_("Description"))
    content_i18n = MapField(StringField(), verbose_name=_("Content"))
    tagline_i18n = MapField(StringField(min_length=0, max_length=100), verbose_name=_("Tagline"))

    # TODO set to required
    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, verbose_name=_("Publisher"))

    creator = ReferenceField(User, reverse_delete_rule=NULLIFY, verbose_name=_("Creator"))
    rule_system = StringField(max_length=60, verbose_name=_("Rule System"))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_("Created on"))
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_("Status"))
    contribution = BooleanField(default=False, verbose_name=_("World accepts contributions"))
    external_host = URLField(verbose_name=_("External host URL"))
    publishing_year = StringField(max_length=4, verbose_name=_("Publishing year"))
    theme = StringField(choices=plugin_choices, null=True, verbose_name=_("Theme"), form="StringField")
    hide_header_text = BooleanField(default=False, verbose_name=_("Hide header text"))

    assets = ListField(EmbeddedDocumentField(Attachment, only=["source_url"]))

    # TODO DEPRECATE in DB version 3
    feature_image = ReferenceField(FileAsset, verbose_name=_("Feature Image"))
    images = ListField(ReferenceField(FileAsset, reverse_delete_rule=NULLIFY), verbose_name=_("World Images"))
    product_url = URLField(verbose_name=_("Product URL"))
    facebook_url = URLField(verbose_name=_("Facebook URL"))

    preferred_license = StringField(
        choices=Licenses.to_tuples(), default=Licenses.ccby4, verbose_name=_("Preferred License")
    )
    languages = ListField(StringField(choices=configured_langs_tuples), verbose_name=_("Available Languages"))
    editors = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_("Editors"))
    readers = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_("Readers"))

    custom_css = StringField(verbose_name=_("Custom CSS"))

    def clean(self):
        for key in self.title_i18n.keys():
            self.title_i18n[key] = self.title_i18n[key].replace("&shy;", "\u00AD")
        # self.title = self.title.replace("&shy;", "\u00AD")  # Replaces soft hyphens with the real unicode
        self.slug = slugify(self.title)
        if self.creator and self.creator not in self.editors:
            self.editors.append(self.creator)
        self.custom_css = secure_css(self.custom_css)

    def __str__(self):
        return self.title

    def articles(self):
        return Article.objects(world=self).order_by("-created_date")

    def is_published(self):
        return self.status == PublishStatus.published and self.created_date <= datetime.utcnow()

    def available_languages(self):
        all = []
        if self.title_i18n:
            all += list(self.title_i18n.items())
        if self.content_i18n:
            all += list(self.content_i18n.items())
        return {k: configured_langs[k] for k, v in all if v and k in configured_langs}

    @property  # For convenience
    def title(self):
        return pick_i18n(self.title_i18n)

    @title.setter
    def set_title(self):
        raise NotImplementedError()

    @property  # For convenience
    def description(self):
        return pick_i18n(self.description_i18n)

    @description.setter
    def set_description(self):
        raise NotImplementedError()

    @property  # For convenience
    def content(self):
        return pick_i18n(self.content_i18n)

    @content.setter
    def set_content(self):
        raise NotImplementedError()

    @property  # For convenience
    def tagline(self):
        return pick_i18n(self.tagline_i18n)

    @tagline.setter
    def set_tagline(self):
        raise NotImplementedError()

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


class WorldMeta(object):
    """This is a dummy World object that means no World, e.g. just articles with a Publisher"""

    slug = "meta"
    languages = []
    editors = []
    title = ""
    creator = None
    theme = ""

    def __init__(self, publisher):
        self.publisher = publisher
        self.title = publisher.title

    def __str__(self):
        return str(self.publisher) or "Meta"

    def __bool__(self):
        return False  # Behave as false

    def articles(self):
        return Article.objects(publisher=self.publisher, world=None).order_by("-created_date")


class RelationType(Document):
    name = StringField()  # human friendly name

    # code = CharField() # parent, child, reference,
    # display = CharField() # some display pattern to use for this relation, e.g. "%from is father to %to"
    # from_type = # type of article from
    # to_type = # type of article to

    def __str__(self):
        return "%s" % self.name


class ArticleRelation(EmbeddedDocument):
    relation_type = ReferenceField(RelationType)
    article = ReferenceField("Article")


class PersonData(EmbeddedDocument):
    born = IntField(verbose_name=_("Born"))
    died = IntField(verbose_name=_("Died"))
    gender = StringField(default=GenderTypes.unknown, choices=GenderTypes.to_tuples(), verbose_name=_("Gender"))
    # otherNames = CharField()
    occupation = StringField(max_length=60, verbose_name=_("Occupation"))

    def gender_name(self):
        return GenderTypes[self.gender]


class FractionData(EmbeddedDocument):
    fraction_type = StringField(max_length=60, verbose_name=_("Fraction"))


class PlaceData(EmbeddedDocument):
    # normalized position system, e.g. form 0 to 1 float, x and y
    coordinate_x = FloatField(verbose_name=_("Coordinate X"))
    coordinate_y = FloatField(verbose_name=_("Coordinate Y"))
    # building, city, domain, point_of_interest
    location_type = StringField(max_length=60, verbose_name=_("Location type"))


class EventData(EmbeddedDocument):
    from_date = IntField(verbose_name=_("From"))
    to_date = IntField(verbose_name=_("To"))


def safeget(dct, *keys):
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return ""
    return dct


class CharacterData(EmbeddedDocument):
    stats = DynamicField()

    def get(self, *keys):
        dct = self.stats
        for key in keys:
            try:
                dct = dct[key]
            except KeyError:
                return ""
        return dct

    def komp_minmax(self):
        attribut = self.get("kompetens")
        minp, maxp, minkomp, maxkomp = 20, 0, None, None
        if attribut:
            try:
                for k, v in attribut.items():
                    for n, p in v.items():
                        if n != "attribut":
                            if p > maxp:
                                maxkomp = n
                                maxp = p
                            elif p < minp:
                                minkomp = n
                                minp = p
            except KeyError:
                pass
        return minkomp, maxkomp


class Episode(EmbeddedDocument):
    id = StringField(unique=True)  # URL-friendly name?
    title = StringField(max_length=60, verbose_name=_("Title"))
    description = StringField(verbose_name=_("Description"))
    content = ListField(ReferenceField("Article"))  # references Article class below


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
    default=_("Default"),
    blogpost=_("Blog Post"),
    material=_("Material"),
    person=_("Person"),
    fraction=_("Fraction"),
    place=_("Place"),
    event=_("Event"),
    campaign=_("Campaign"),
    chronicles=_("Chronicle"),
    character=_("Character"),
)

# Ideas for unicode symbols of above
# ✪ ✵ ✯ ♖ ♜ ❦ ♕ ✎ ✉ ⁂ ※ ⌘ ⚐ ⚔ ⚜ ⚥ 👤
# dice ⚀ ⚁ ⚂ ⚃ ⚄ ⚅


# Those types that are actually EmbeddedDocuments. Other types may just be strings without metadata.
EMBEDDED_TYPES = ["persondata", "fractiondata", "placedata", "eventdata", "campaigndata", "characterdata"]


class RemoteImage:
    def __init__(self, url):
        self.url = url
        self.slug = url

    def feature_url(self, **kwargs):
        crop = kwargs.pop("crop", None)
        if crop and len(crop) >= 2:
            # https://res.cloudinary.com/demo/image/upload/w_250,h_250,c_limit/sample.jpg
            crop_type = "lfill" if len(crop) != 3 else crop[2]
            s = f"/upload/w_{crop[0]},h_{crop[1]},c_{crop_type},g_auto/"
            return self.url.replace("/upload/", s)
        return self.url


class Article(Document):
    meta = {
        "indexes": ["slug", {"fields": ["$title", "$content", "$tags"]}],
        # 'auto_create_index': True
    }
    slug = StringField(unique=True, required=False, max_length=62)
    type = StringField(choices=ArticleTypes.to_tuples(), default=ArticleTypes.default, verbose_name=_("Type"))
    world = ReferenceField(World, reverse_delete_rule=DENY, verbose_name=_("World"))
    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, verbose_name=_("Publisher"))
    creator = ReferenceField(User, verbose_name=_("Creator"))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_("Created"))
    title = StringField(min_length=1, max_length=60, required=True, verbose_name=_("Title"))  # TODO i18n
    description = StringField(max_length=350, verbose_name=_("Description"))  # TODO i18n
    content = StringField(verbose_name=_("Content"))  # TODO i18n
    status = StringField(choices=PublishStatus.to_tuples(), default=PublishStatus.published, verbose_name=_("Status"))
    tags = ListField(StringField(max_length=60), verbose_name=_("Tags"))
    theme = StringField(choices=plugin_choices, null=True, verbose_name=_("Theme"))
    hide_header_text = BooleanField(default=False, verbose_name=_("Hide header text"))

    # Sort higher numbers first, lower later. Top 5 highest numbers used to
    sort_priority = IntField(default=0, verbose_name=_("Sort priority"))
    language = StringField(
        choices=configured_langs_tuples,
        default=default_locale.language if default_locale else "",
        verbose_name=_("Language"),
    )

    translations_i18n = MapField(ReferenceField("Article"), verbose_name=_("Translations"),)

    # TODO DEPRECATE in DB version 3
    featured = BooleanField(default=False, verbose_name=_("Featured article"))
    feature_image = ReferenceField(FileAsset, reverse_delete_rule=NULLIFY, verbose_name=_("Feature Image"))
    cloudinary = StringField()

    images = ListField(ReferenceField(FileAsset, reverse_delete_rule=NULLIFY), verbose_name=_("Images"))
    license = StringField(choices=Licenses.to_tuples(), default=Licenses.ccby4, verbose_name=_("License"))
    editors = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_("Editors"))
    readers = ListField(ReferenceField(User, reverse_delete_rule=NULLIFY), verbose_name=_("Readers"))
    custom_css = StringField(verbose_name=_("Custom CSS"))
    shortcut = ReferenceField("Shortcut", verbose_name=_("Shortcut"))

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
        return "%s - %s" % (self.world or self.world or "Lore", self)

    @property  # For convenience
    def get_feature_image(self):
        # Smallest aspect
        if self.cloudinary:
            return RemoteImage(self.cloudinary)
        else:
            newlist = sorted(self.images, key=lambda x: x.aspect_ratio())
            return newlist[0] if newlist else None

    @property  # For convenience
    def get_header_image(self):
        # Largest aspect
        newlist = sorted(self.images, key=lambda x: x.aspect_ratio(), reverse=True)
        return newlist[0] if newlist and newlist[0].aspect_ratio() > 1 else None

    # Executes before saving
    def clean(self):
        self.title = self.title.replace("&shy;", "\u00AD")  # Replaces soft hyphens with the real unicode
        self.slug = slugify(self.title)
        if self.creator and self.creator not in self.editors:
            self.editors.append(self.creator)

    def is_published(self):
        return self.status == PublishStatus.published and self.created_date <= datetime.utcnow()

    def status_name(self):
        return PublishStatus[self.status] + (
            (
                " %s %s" % (_("from"), str(self.created_date))
                if self.status == PublishStatus.published and self.created_date >= datetime.utcnow()
                else ""
            )
        )

    def available_languages(self):
        """Returns as a dict of locales

        Returns:
            [dict]: dict of locales
        """
        langs = [self.language] if self.language else []
        langs += [lang for lang, id in self.translations_i18n.items() if id]
        return {lang: configured_langs.get(lang) for lang in langs if lang in configured_langs}

    def shortcut_suggestions(self):
        return shorten(self.slug)

    @staticmethod
    def type_data_name(asked_type):
        return asked_type + "data"

    def __str__(self):
        return "%s%s" % (self.title, " [%s]" % self.type)

    persondata = EmbeddedDocumentField(PersonData)
    fractiondata = EmbeddedDocumentField(FractionData)
    placedata = EmbeddedDocumentField(PlaceData)
    eventdata = EmbeddedDocumentField(EventData)
    campaigndata = EmbeddedDocumentField(CampaignData)
    characterdata = EmbeddedDocumentField(CharacterData)
    relations = ListField(EmbeddedDocumentField(ArticleRelation))


Article.language.filter_options = choice_options("language", Article.language.choices)
Article.type.filter_options = choice_options("type", Article.type.choices)
Article.status.filter_options = choice_options("status", Article.status.choices)
Article.world.filter_options = reference_options("world", Article)
Article.tags.filter_options = distinct_options("tags", Article)
Article.created_date.filter_options = datetime_delta_options(
    "created_date", [timedelta(days=7), timedelta(days=30), timedelta(days=90), timedelta(days=365)]
)


class Shortcut(Document):
    meta = {"indexes": ["slug"]}
    url = URLField(verbose_name=_("External URL"))
    slug = StringField(unique=True, required=True, max_length=10, verbose_name=_("Slug"))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_("Created on"))
    hits = IntField(min_value=0, verbose_name=_("Hits"))
    description = StringField(max_length=500, verbose_name=_("Description"))
    article = ReferenceField(Article, reverse_delete_rule=NULLIFY, verbose_name=_("Article"))

    def clean(self):
        self.slug = slugify(self.slug)  # Force slugify as it may be invalid otherwise
        if self.article:
            self.url = None
        elif self.url:
            self.article = None

    def short_url(self):
        return url_for("world.shorturl", code=self.slug, _external=True)


Shortcut.created_date.filter_options = datetime_delta_options(
    "created_date", [timedelta(days=7), timedelta(days=30), timedelta(days=90), timedelta(days=365)]
)
Shortcut.register_delete_rule(Article, "shortcut", NULLIFY)


def import_article(row, commit=False):
    """The model method for importing to Article from text-based data in row"""
    article = Article()
    warnings = []
    title = get(row, "Title", "")
    content = get(row, "Content", "")
    shortcode = get(row, "Shortcode", "").lower()
    created = get(row, "Created", "")
    status = get(row, "Status", "")
    publisher = get(row, "Publisher", "")
    world = get(row, "World", "")
    creator_email = get(row, "Creator", "").lower()
    if not title:
        raise ValueError("Missing compulsory column Title")
    if shortcode:
        count = Shortcut.objects(slug=shortcode).count()
        if count > 0:
            raise ValueError(f"The shortcode {shortcode} is already taken")
    article.created_date = datetime.datetime.strptime(created, "%Y-%m-%d")
    article.creator, created = user_from_email(creator_email, create=True, commit=commit)
    if status:
        if status not in PublishStatus:
            raise ValueError(f"Publish Status {status} is invalid")
        else:
            article.status = status
    if publisher:
        article.publisher = Publisher.objects(slug=publisher).scalar("id").as_pymongo().get()["_id"]
    if world:
        article.world = World.objects(slug=world).scalar("id").as_pymongo().get()["_id"]
    article.title = title
    article.content = content
    if commit:
        article.save()
        if shortcode:
            sh = Shortcut(slug=shortcode, article=article.id)
            sh.save()
            article.shortcut = sh
            article.save()

    results = dict(row)
    results["Email"] = article.creator
    results["Publisher"] = article.publisher
    results["World"] = article.world
    results["Created"] = article.created_date
    return article, results, warnings
