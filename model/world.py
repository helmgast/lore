from raconteur import db
from misc import slugify, now
from user import User, Group

'''
Created on 2 jan 2014

@author: Niklas
'''

# Constants and enumerations
ARTICLE_DEFAULT, ARTICLE_MEDIA, ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT, ARTICLE_CAMPAIGN, ARTICLE_CHRONICLE = 0, 1, 2, 3, 4, 5, 6, 7
ARTICLE_TYPES = ((ARTICLE_DEFAULT, 'default'),
                 (ARTICLE_MEDIA, 'media'),
                 (ARTICLE_PERSON, 'person'),
                 (ARTICLE_FRACTION, 'fraction'),
                 (ARTICLE_PLACE, 'place'),
                 (ARTICLE_EVENT, 'event'),
                 (ARTICLE_CAMPAIGN, 'campaign'),
                 (ARTICLE_CHRONICLE, 'chronicle'))

PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_REVISION, PUBLISH_STATUS_PUBLISHED = 0, 1, 2
PUBLISH_STATUS_TYPES = ((PUBLISH_STATUS_DRAFT, 'draft'),
                        (PUBLISH_STATUS_REVISION, 'revision'),
                        (PUBLISH_STATUS_PUBLISHED, 'published'))

GENDER_UNKNOWN, GENDER_MALE, GENDER_FEMALE = 0, 1, 2
GENDER_TYPES = ((GENDER_UNKNOWN, 'unknown'),
                (GENDER_MALE, 'male'),
                (GENDER_FEMALE, 'female'))

class MediaResource(db.Document):
    mime_type = db.StringField()
    file = db.FileField() # Check ImageField?
    size_x = db.IntField()
    size_y = db.IntField()

class World(db.Document):
    slug = db.StringField(unique=True) # URL-friendly name
    title = db.StringField()
    description = db.StringField()
    thumbnail = db.ReferenceField(MediaResource)
    publisher = db.StringField()
    rule_system = db.StringField()
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


class Article(db.Document):
    meta = {'allow_inheritance': True, 'indexes': ['slug']} 
    slug = db.StringField() # URL-friendly name, removed "unique", slug cannot be guaranteed to be unique
    type = db.IntField(choices=ARTICLE_TYPES, default=ARTICLE_DEFAULT)
    world = db.ReferenceField(World)
    creator = db.ReferenceField(User)
    created_date = db.DateTimeField(default=now)
    title = db.StringField()
    description = db.StringField()
    content = db.StringField()
    thumbnail = db.ReferenceField(MediaResource)
    status = db.IntField(choices=PUBLISH_STATUS_TYPES, default=PUBLISH_STATUS_DRAFT)
    # modified_date = DateTimeField()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super(Article, self).save(*args, **kwargs)
      
    def is_person(self):
        return ARTICLE_PERSON == self.type

    def is_media(self):
        return ARTICLE_MEDIA == self.type

    def type_name(self):
        return ARTICLE_TYPES[self.type][1]

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return u'%s%s' % (self.title, ' [%s]' % self.type_name() if self.type > 0 else '')

class MediaArticle(Article):
    media = db.ReferenceField(MediaResource)

class PersonArticle(Article):
    born = db.IntField()
    died = db.IntField()
    gender = db.IntField(default=GENDER_UNKNOWN, choices=GENDER_TYPES)
    # otherNames = CharField()
    occupation = db.StringField()

    def gender_name(self):
        return GENDER_TYPES[self.gender][1].title()

class FractionArticle(Article):
    fraction_type = db.StringField()

class PlaceArticle(Article):
    # normalized position system, e.g. form 0 to 1 float, x and y
    coordinate_x = db.FloatField() 
    coordinate_y = db.FloatField()
    # building, city, domain, point_of_interest
    location_type = db.StringField()

class EventArticle(Article):
    from_date = db.IntField()
    to_date = db.IntField()

class Episode(db.EmbeddedDocument):
    id = db.StringField(unique=True) # URL-friendly name?
    title = db.StringField()
    description = db.StringField()
    content = db.ListField(db.ReferenceField(Article))
    
Episode.children = db.ListField(db.EmbeddedDocumentField(Episode))
    
class CampaignArticle(Article):
    children = db.ListField(db.EmbeddedDocumentField(Episode))

class ChronicleArticle(Article):
    pass


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
    article = db.ReferenceField(Article)
    relation_type = db.ReferenceField(RelationType)

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return u'%s %s %s' % (self.from_article.title, self.relation_type, self.to_article.title)

Article.relations = db.ListField(db.EmbeddedDocumentField(ArticleRelation))


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

'''
@ link to
& embed
# revision
World:Mundana
    &Text:...  (always a leaf node)
    &Media:... (also always a leaf node)
    @Place:Consaber
        @Place:Nantien
            @Person:Tiamel
            @Place:Nant
                #rev67
                #rev66
                ...
    Event:Calniafestivalen
    Scenario:Calniatrubbel
        &Text:...
        @Scene:1
            @/mundana/consaber/nantien
            @/mundana/
        @Scene:2
        @Scene:3
    Character:Taldar

Semantical structure
World:Mundana
    Place:Consaber mundana/consaber
        Place:Nantien mundana/consaber/nantien
            Person:Tiamel mundana/consaber/nantien/tiamel
            Place:Nant mundana/consaber/
    Event:Calniafestivalen
    Scenario:Calniatrubbel
        Scene:1
            @/mundana/consaber/nantien
            @/mundana/
        Scene:2
        Scene:3
    Character:Taldar
'''