import json
import logging
from datetime import datetime, timedelta

from flask import current_app, url_for, g
from flask_babel import lazy_gettext as _
from mongoengine import (Document, EmbeddedDocument, StringField, DateTimeField, FloatField, LazyReferenceField, BooleanField,
                         ListField, IntField, EmailField, EmbeddedDocumentListField, DynamicField, URLField, NULLIFY, DENY)



logger = current_app.logger if current_app else logging.getLogger(__name__)

basic_topics = {
    # Occurrence instanceOfs
    'article': "",
    'audio': "",
    'bibref': "",
    'comment': "",
    'date-of-birth': "",
    'date-of-death': "",
    'started-at': "",
    'stopped-at': "",
    'description': "",
    'gallery': "",
    'image': "",
    'video': "",
    'website': "",
    'google-doc': "",  # Special GDoc occurrence to populate the article
    'qr-code': "",
    'prev': "",
    'next': "",
    'pdf': "",
    '3d-model': "",
    'map-point': "",
    'map-geopoint': "",
    'map-polygon': "",
    'map-geopolygon': "",
    'map-geopolygon': "",
    'version': "",
    'creator': "",
    'created-at': "",
    'updated-at': "",
    'license': "",

    # Associations instanceOf
    'association': "",  # member association member
    'categorizes-as': "",  # instance categorizes-as category    
    'located-in': "",  # containee located-in container
    'is-a': "",  # subtype is-a supertype
    'appears-in': "",  # character appears-in work
    'born-in': "",  # person born-in birthplace
    'died-in': "",  # person died-in deathplace
    'killed-by': "",  # victim killed-by perpetrator
    'son-father': "",  # son son-father father 
    'son-mother': "",  # son son-mother mother 
    'daughter-mother': "",  # daughter daughter-mother mother 
    'daughter-father': "",  # daughter daughter-father father 
    'related-to': "",  # relative related-to relative
    'espouses': "",  # spouse espouses spouse
    'part-of': "",  # part part-of whole
    'rules': "",  # ruler rules domain
    'member-of': "",  # member member-of organization
    'mentions': "",  # mentioner mentions target
    'descends-from': "",  # descendant descends-from ancestor

    # Lore topics
    'world': "",
    'person': "",
    'character': "",
    'domain': "",  # A country, state, area etc with a ruler
    'place': "",  # A specific location
    'concept': "",
    'faction': "",  # A group of people with an agenda
    'item': "",
    'event': "",

    # Scope topics
    '*': "",  # Universal scope
    'en_us': "",
    'sv_se': "",
    'canon-content': "",  # Denotes a characteristic as canon
    'contrib-content': "",  # Denotes a characteristic as contributed, not yet approved
    'community-content': ""  # Denotes a characteristic as approved community material
}

# Scopes
# States that a Name/Occurrence/Association is only valid only certain circumstances.
# E.g. might only be valid within a certain time frame, might be non-canonical proposal, or might be a localized variant (mostly names).

# You can filter topics by scope. Either you can look for topics with ANY of the search scopes, or with ALL of the search scopes. An empty
# scope is always valid.


class Name(EmbeddedDocument):
    name = StringField()
    scopes = ListField(LazyReferenceField('Topic'))  # Expected to always be sorted


class Occurrence(EmbeddedDocument):
    uri = URLField()
    content = StringField()  # Could be any inline data?
    instance_of = LazyReferenceField('Topic')
    scopes = ListField(LazyReferenceField('Topic'))  # Expected to always be sorted


class Association(EmbeddedDocument):
    this_topic = LazyReferenceField('Topic')
    this_role = LazyReferenceField('Topic')  # E.g. Employs
    instance_of = LazyReferenceField('Topic')  # E.g. Employment (association types should be nouns to make them uni-directional)
    other_role = LazyReferenceField('Topic')  # E.g. employed by
    other_topic = LazyReferenceField('Topic')
    scopes = ListField(LazyReferenceField('Topic'))  # Expected to always be sorted


_noval = object()


class Topic(Document):
    id = StringField(primary_key=True)
    description = StringField()  # Should be multi-language
    instance_of = LazyReferenceField('Topic')
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    names = EmbeddedDocumentListField(Name)
    occurrences = EmbeddedDocumentListField(Occurrence)
    associations = EmbeddedDocumentListField(Association)

    def get_name(self, index=0):
        try:
            return self.names[index].name
        except IndexError:
            return self.id

    def find_occurrences(self, uri=_noval, content=_noval, instance_of=_noval, scopes=_noval):
        """Finds occurrences on this topic that matches the complete or partial arguments.
        Returns a list.
        """
        if scopes != _noval:
            scopes = sorted(scopes)
        return [x for x in self.occurrences if
                (uri == _noval or uri == x.uri) or
                (content == _noval or content == x.content) or
                (instance_of == _noval or instance_of == x.instance_of.id) or
                (scopes == _noval or scopes == x.scopes)]

    def find_associations(self, this_role=_noval, instance_of=_noval, other_role=_noval, other_topic=_noval, scopes=_noval):
        """Finds associations on this topic that matches the complete or partial arguments.
        Returns a list.
        """
        if scopes != _noval:
            scopes = sorted(scopes or [])
        return [x for x in self.associations if
                (this_role == _noval or this_role == x.this_role.id) or
                (instance_of == _noval or instance_of == x.instance_of.id) or
                (other_role == _noval or other_role == x.other_role.id) or
                (other_topic == _noval or other_topic == x.other_topic.id) or
                (scopes == _noval or scopes == x.scopes)]

    def find_names(self, name=_noval, scopes=_noval):
        """Finds names on this topic that matches the complete or partial arguments.
        Returns a list.
        """
        if scopes != _noval:
            scopes = sorted(scopes)

        return [x for x in self.names if
                (name == _noval or name == x.name) or
                (scopes == _noval or scopes == x.scopes)
                ]

    def add_name(self, name, scopes=None):
        """ Add a new name unless equal to existing name and scopes in list.
        name -- a string
        scopes -- a list of topic id strings
        """
        if scopes is None:
            scopes = []
        if not self.find_names(name, scopes):
            self.names.append(Name(name=name, scopes=scopes))

    def add_occurrence(self, uri=None, content=None, instance_of=None, scopes=None):
        """ Add a new occurrence unless identical with existing.
        name -- a string
        scopes -- a list of topic id strings
        """
        if uri is None and content is None:
            raise ValueError("Need at least an URI or content")
        if instance_of is None:
            instance_of = "website" if uri else "description"
        if scopes is None:
            scopes = []
        # If two occurrences have same uri/description/instance_of but different scopes, are they different?
        # Or should we just add the scope to existing?
        if not self.find_occurrences(uri, content, instance_of, scopes):
            self.occurrences.append(Occurrence(uri=uri, content=content, instance_of=instance_of, scopes=scopes))

    def add_association(self, other_topic, instance_of="association", this_role="member", other_role="member", scopes=None):
        """ Add a new association from this topic to another topic.
        """
        if scopes is None:
            scopes = []
        self.find_associations(this_role=this_role, instance_of=instance_of, other_role=other_role, other_topic=other_topic)
        ass = Association(this_topic=self, other_topic=other_topic, instance_of=instance_of, this_role=this_role, other_role=other_role, scopes=scopes)
        self.associations.append(ass)
        # Fetch reference if we got an id. Otherwise, we assume we have a Topic object already (supporting use without a database)
        if isinstance(other_topic, str):
            other_topic = Topic.objects(id=other_topic).get()
        # On other topic, "this" and "other" will be reversed.
        if not other_topic.find_associations(this_role=other_role, instance_of=instance_of, other_role=this_role, other_topic=self):
            other_topic.associations.append(Association(
                this_topic=other_topic, other_topic=self, instance_of=instance_of, this_role=other_role, other_role=this_role, scopes=scopes))

        # A:
        #   ass = [this: A, other: B, instance: ass, this_role: member, other_role: member]
        # B:
        #   ass = [this: B, other: A, instance: ass, this_role: member, other_role: member]

    def __str__(self):
        return f"{self.get_name()} ({self.id}, {self.created_at})"

    def __repr__(self):
        return json.dumps(json.loads(self.to_json()), indent=2)
