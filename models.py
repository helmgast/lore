from hashlib import md5
import datetime
from wtfpeewee.orm import model_form
from flask_peewee.auth import BaseUser
from flask_peewee.utils import slugify
from peewee import *
from peewee import RawQuery
from raconteur import db

# WTForms would treat the _absence_ of a field in POST data as a reason to
# to set the data to empty. This is a problem if the same POST receives variations
# to a form. This method removes form fields if they are not present in postdata.
# This means the form logic will not touch those fields in the actual objects.
def matches_form(formclass, formdata):
    for k in formdata.iterkeys():
        if k in dir(formclass):
            print "Matches field %s!" % k
            return True
    return False

class Conversation(db.Model):
    #creator = ForeignKeyField(User)
    modified_date = DateTimeField(default=datetime.datetime.now)
    
    def members(self):
        return User.select().join(ConversationMember).where(ConversationMember.conversation == self)
        
    def last_message(self):
        msgs = list(Message.select().where(Message.conversation == self).order_by(Message.pub_date.desc()).limit(1))
        if len(msgs)==0:
            return None
        return msgs[0]
        
    def add_members(self, members):
        for m in members:
            ConversationMember.create(member=m, conversation=self)
            m.log("was added to conversation %s" % self.id)

    def __unicode__(self):
        return u'conversation'
    
# A user in the system
class User(db.Model, BaseUser):
    username = CharField()
    password = CharField()
    email = CharField()
    realname = CharField()
    location = CharField(null=True)
    description = TextField(null=True)
    exp = IntegerField(default=0)
    join_date = DateTimeField(default=datetime.datetime.now)
    msglog = ForeignKeyField(Conversation)
    active = BooleanField(default=True)
    admin = BooleanField(default=False)

    def __unicode__(self):
        return self.username

    def save(self, *args, **kwargs):
        print "args, %s, kwargs %s" % (args, kwargs)
        try:
            self.msglog.get()
        except Conversation.DoesNotExist:
            print "No log, creating"
            self.msglog = Conversation.create()
            print "Now have %s" % self.msglog.id
        return super(User, self).save(*args, **kwargs)

    def full_string(self):
        return "%s (%s)" % (self.username, self.realname)
     
    def log(self, msg):
        print self.username,msg
        Message.create(user=self, content=msg, conversation=self.msglog)

    def groups(self):
        return Group.select().join(GroupMember).where(GroupMember.member == self)

    def messages(self):
        return Message.select().where(Message.user == self).order_by(Message.pub_date.desc())

    # Users that this user follows
    def following(self):
        return User.select().join(
            Relationship, on=Relationship.to_user
        ).where(Relationship.from_user == self).order_by(User.username.asc())

    # Users that follows this user
    def followers(self):
        return User.select().join(
            Relationship, on=Relationship.from_user
        ).where(Relationship.to_user == self).order_by(User.username.asc())
    
    def is_following(self, user):
        return Relationship.filter(
            from_user=self,
            to_user=user
        ).exists()
        
    def get_most_recent_conversation_with(self, recipients):
        # A private conversation is one which is only between this user
        # and the given recipients, with no other users
        if not recipients:
            raise ValueError('Empty list of recipients')
        if not isinstance(recipients, list) or not isinstance(recipients[0], User):
            raise TypeError('Expects a list of User')
        print "recipients is list of %s, first item is %s" % (type(recipients[0]), recipients[0])
        member_ids = [self.id]+[i.id for i in recipients] # add this user as well

        rq = RawQuery(Conversation, 
            'SELECT c.id, c.modified_date FROM conversation c INNER JOIN \
            conversationmembers a ON a.conversation_id = c.id WHERE a.member_id IN (?%s) GROUP BY \
            a.conversation_id HAVING COUNT(*) = ( SELECT COUNT(*) FROM conversationmembers b \
            WHERE b.conversation_id = a.conversation_id GROUP BY b.conversation_id) AND COUNT(*) = ? \
            ORDER BY c.modified_date DESC;' % ',?'*(len(member_ids)-1),
            *(member_ids+[len(member_ids)]))
        # NOTE, the query need to include a ? for each parameter, so we need to insert enough ? to match
        # our number of members. We also need to insert the number of members as a parameter itself,
        # into the last function argument, in the *params style (expand list into separate arguments)
        #print rq.sql(db.get_compiler())
        return rq

    def gravatar_url(self, size=48):
        return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' %\
               (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

    @classmethod
    def get_form(cls):
        return model_form(User, exclude=['password','admin', 'active', 'exp','username', 'join_date'])

    @classmethod
    def allowed(cls, user, op='view', instance=None):
        if user:
            if op=='view' or op=='new':
                return True
            else:
                return (user.id == instance.id) # requesting user and passed user instance has same ID - you can edit yourself
        return False

# An autogenerated form class for doing validation and POST / form processing
UserForm = User.get_form()

class ConversationMember(db.Model):
    member = ForeignKeyField(User)
    conversation = ForeignKeyField(Conversation)

# A gamer group, e.g. people who regularly play together. Has game masters
# and players
class Group(db.Model):
    name = CharField()
    location = CharField()
    slug = CharField()
    description = CharField()
    conversation = ForeignKeyField(Conversation)
    
    def __unicode__(self):
        return self.slug

    # Need to add *args, **kwargs for some arcane reason
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        try:
            self.conversation.get()
        except Conversation.DoesNotExist:
            print "No conversation, creating"
            self.conversation = Conversation.create()
            print "Now have %s" % self.conversation.id
        return super(Group, self).save(*args, **kwargs)
    
    # def create(self, *args, **kwargs):
    #     self.conversation = Conversation.create()
    #     return super(Group, self).create(*args, **kwargs)

    def masters(self):
        return User.select().join(GroupMember).where(GroupMember.group == self, GroupMember.status == GROUP_MASTER)
    def players(self):
        return User.select().join(GroupMember).where(GroupMember.group == self, GroupMember.status == GROUP_PLAYER)
    def invited(self):
        return User.select().join(GroupMember).where(GroupMember.group == self, GroupMember.status == GROUP_INVITED)
    def members(self):
        return GroupMember.select().where(GroupMember.group == self).order_by(GroupMember.status.asc())

    def get_member(self, user):
        return GroupMember.get(member=user,group=self)

    def addMembers(self, newmembers, type):
        if not newmembers or not isinstance(newmembers[0], User):
            raise TypeError("Need a list of Users, got %s of type %s" % (newmembers, type(newmembers)))
        if not type in STATUSES.keys():
            raise TypeError("type need to be one predefined integers, see models.py")
        members_dict = dict([[gm.member.id,gm] for gm in GroupMember.select().where(GroupMember.group == self)])
        edited = []
        for u in newmembers:
            if u.id in members_dict:
                if type==GROUP_MASTER and members_dict[u.id].status == GROUP_PLAYER: # Upgrade user to master
                    members_dict[u.id].status = GROUP_MASTER
                    members_dict[u.id].save()
                    edited.append(members_dict[u.id])
                    u.log("was upgraded to Master of %s" % self.slug)
            else:
                edited.append(GroupMember.create(group=self, member=u, status=type))
                u.log("was added to group %s" % self.slug)
        return edited

    def removeMembers(self, members):
        if not members or not isinstance(members[0], User):
            raise TypeError("Need a list of Users, got %s of type %s" % (members, type(members)))
        removed = []
        for gm in GroupMember.select().where(GroupMember.group == self, GroupMember.member << members): # in members
            removed.append(gm)
            cm = ConversationMember.get(conversation=self.conversation, member=gm.member)
            gm.member.log("was removed from group %s" % self.slug)
            gm.delete_instance()
            cm.delete_instance() # Remove the user from the group conversation as well
        return removed
                        
# The relationship between a user as member of a Group
GROUP_MASTER, GROUP_PLAYER, GROUP_INVITED = 1,2,3
STATUSES = {GROUP_MASTER:'master', GROUP_PLAYER:'player', GROUP_INVITED:'invited'}
class GroupMember(db.Model):
    group = ForeignKeyField(Group)
    member = ForeignKeyField(User)
    status = IntegerField(choices=((GROUP_MASTER, 'master'), (GROUP_PLAYER, 'player'), (GROUP_INVITED, 'invited')))
    
    def __unicode__(self):
        return "%s, %s in %s" % (self.member, self.status_text(), self.group)

    def save(self, *args, **kwargs):
        if self.member not in self.group.conversation.members():
            self.group.conversation.add_members([self.member])
        return super(GroupMember, self).save(*args, **kwargs)

    def status_text(self):
        return STATUSES[self.status]

# The directional relationship between two users, e.g. from_user follows to_user
class Relationship(db.Model):
    from_user = ForeignKeyField(User, related_name='relationships')
    to_user = ForeignKeyField(User, related_name='related_to')

    def __unicode__(self):
        return 'Relationship from %s to %s' % (self.from_user, self.to_user)
        
# A message from a user (to everyone)
class Message(db.Model):
    user = ForeignKeyField(User)
    content = TextField()
    pub_date = DateTimeField(default=datetime.datetime.now)
    conversation = ForeignKeyField(Conversation, null=True)
    #readable_by = IntegerField(choices=((1, 'user'), (2, 'group'), (3, 'followers'), (4, 'all')))

    def __unicode__(self):
        return '%s: %s' % (self.user, self.content)
  
class World(db.Model):
    title = CharField()
    slug = CharField(unique=True) # URL-friendly name
    description = TextField(null=True)
    publisher = CharField(null=True)
    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super(World, self).save(*args, **kwargs)
    def __unicode__(self):
        return self.title+(' by '+self.publisher) if self.publisher else ''

    # startyear = 0
    # daysperyear = 360
    # datestring = "day %i in the year of %i" 
    # calendar = [{name: january, days: 31}, {name: january, days: 31}, {name: january, days: 31}...]

# All material related to a certain story.
class Campaign(db.Model):
    name = CharField()
    slug = CharField()
    world = ForeignKeyField(World, related_name='campaigns')
    group = ForeignKeyField(Group)
    rule_system = CharField()
    description = TextField(null=True)
    archived = BooleanField(default=False) # If the campaign is archived
    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super(Campaign, self).save(*args, **kwargs)

    def load_scene_tree(self, scene_tree, parent=None):
        # TODO very inefficient implementation
        o = 1
        for s in scene_tree:
            print "Found %s, updating to o=%s, parent=%s" % (s, o, parent)
            q = Scene.update(order=o, parent=parent).where(Scene.id == s['id'])
            print q.execute()
            o += 1
            if 'children' in s:
                self.load_scene_tree(s['children'], parent=Scene.get(Scene.id == s['id'])) 

# A part of a Scenario, that can be in current focus of a game
class Scene(db.Model):
    campaign = ForeignKeyField(Campaign)
    parent = ForeignKeyField('self', related_name='children', null=True)
    name = CharField()
    description = CharField(null=True)
    order = IntegerField() # The integer order between scenes

    def ordered_children(self):
        return self.children.order_by(Scene.order.asc())
                
# A game session that was or will be held, e.g. the instance between a scenario
# and a group at a certain date
class Session(db.Model):
    play_start = DateTimeField()
    play_end = DateTimeField()
    campaign = ForeignKeyField(Campaign, related_name='sessions')
    description = CharField(null=True) # Details on the event if any.
    location = CharField(null=True) # Location of the session

# Lists users present at a particular session
class SessionPresentUser(db.Model):
    present_user = ForeignKeyField(User)
    session = ForeignKeyField(Session)
            
class GeneratorInputList(db.Model):
    name = CharField()

    def items(self):
        return GeneratorInputItem.select().where(GeneratorInputItem.input_list == self)

class GeneratorInputItem(db.Model):
    input_list = ForeignKeyField(GeneratorInputList)
    content = CharField()

class StringGenerator(db.Model):
    name = CharField()
    description = TextField(null=True)
    generator = None

    def __unicode__(self):
        return self.name

ARTICLE_DEFAULT, ARTICLE_MEDIA, ARTICLE_PERSON, ARTICLE_FRACTION, ARTICLE_PLACE, ARTICLE_EVENT = 0, 1, 2, 3, 4, 5
ARTICLE_TYPES = ((ARTICLE_DEFAULT, 'default'), (ARTICLE_MEDIA, 'media'), (ARTICLE_PERSON, 'person'), (ARTICLE_FRACTION, 'fraction'), (ARTICLE_PLACE, 'place'), (ARTICLE_EVENT, 'event'))

class Article(db.Model):
    type = IntegerField(default=ARTICLE_DEFAULT, choices=ARTICLE_TYPES)
    world = ForeignKeyField(World, related_name='articles')
    title = CharField()
    slug = CharField(unique=True) # URL-friendly name
    content = TextField()
 
    # publish_status = IntegerField(choices=((1, 'draft'),(2, 'revision'), (3, 'published')), default=1)
    created_date = DateTimeField(default=datetime.datetime.now)
    # modified_date = DateTimeField()
    # thumbnail

    def remove_old_type(self, newtype):
        if self.type != newtype:  
            # First clean up old reference
            typeobj = self.get_type()
            print "We have changed type from %d to %d, old object was %s" % (self.type, newtype, typeobj)
            if typeobj:
                print typeobj.delete_instance(recursive=True) # delete this and references to it

    def get_type(self):
        if self.type==ARTICLE_MEDIA:
            return self.mediaarticle.first()
        elif self.type==ARTICLE_PERSON:
            return self.personarticle.first()
        elif self.type==ARTICLE_FRACTION:
            return self.fractionarticle.first()
        elif self.type==ARTICLE_PLACE:
            return self.placearticle.first()
        elif self.type==ARTICLE_EVENT:
            return self.eventarticle.first()
        else:
            return None

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super(Article, self).save(*args, **kwargs)

    def delete_instance(self, recursive=False, delete_nullable=False):
        # We need to delete the article_type first, because it has no reference back to this
        # object, and would therefore not be caught by recursive delete on the row below
        self.get_type().delete_instance(recursive=True)
        return super(Article, self).delete_instance(recursive, delete_nullable)

    def is_person(self):
        return ARTICLE_PERSON == self.type

    def is_media(self):
        return ARTICLE_MEDIA == self.type

    def type_name(self, intype=None):
        if intype:
            if isinstance(intype, basestring):
                intype = int(intype)
            return ARTICLE_TYPES[intype][1]
        return ARTICLE_TYPES[self.type][1]

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return u'%s [%s]' % (self.title, self.world.title)

class MediaArticle(db.Model):
    article = ForeignKeyField(Article, related_name='mediaarticle')
    mime_type = CharField()
    url = CharField()

GENDER_UNKNOWN, GENDER_MALE, GENDER_FEMALE = 0, 1, 2
GENDER_TYPES = ((GENDER_UNKNOWN, 'unknown'), (GENDER_MALE, 'male'), (GENDER_FEMALE, 'female'))
class PersonArticle(db.Model):
    article = ForeignKeyField(Article, related_name='personarticle')
    born = IntegerField(null=True)
    died = IntegerField(null=True)
    gender = IntegerField(default=GENDER_UNKNOWN, choices=GENDER_TYPES)
    # otherNames = CharField()
    occupation = CharField(null=True)

    def gender_name(self):
        return GENDER_TYPES[self.type][1].title()

class FractionArticle(db.Model):
    article = ForeignKeyField(Article, related_name='fractionarticle')
    fraction_type = CharField()

class PlaceArticle(db.Model):
    article = ForeignKeyField(Article, related_name='placearticle')
    coordinate_x = FloatField(null=True) # normalized position system, e.g. form 0 to 1 float, x and y
    coordinate_y = FloatField(null=True) # 
    location_type = CharField() # building, city, domain, point_of_interest

class EventArticle(db.Model):
    article = ForeignKeyField(Article, related_name='eventarticle')
    from_date = IntegerField()
    to_date = IntegerField()

ARTICLE_CREATOR, ARTICLE_EDITOR, ARTICLE_FOLLOWER = 0, 1, 2
ARTICLE_USERS = ((ARTICLE_CREATOR, 'creator'), (ARTICLE_EDITOR,'editor'), (ARTICLE_FOLLOWER,'follower'))
class ArticleUser(db.Model):
    article = ForeignKeyField(Article, related_name='user')
    user = ForeignKeyField(User)
    type = IntegerField(default=ARTICLE_CREATOR, choices=ARTICLE_USERS)

class RelationType(db.Model):
    name = CharField() # human friendly name
    # code = CharField() # parent, child, reference, 
    # display = CharField() # some display pattern to use for this relation, e.g. "%from is father to %to"
    # from_type = # type of article from
    # to_type = # type of article to 
    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return u'%s' % self.name

class ArticleRelation(db.Model):
    from_article = ForeignKeyField(Article, related_name='outgoing_relations')
    to_article = ForeignKeyField(Article, related_name='incoming_relations')
    relation_type = ForeignKeyField(RelationType, related_name='relations')
    # twosided = False, True

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return u'%s %s %s' % (self.from_article.title, self.relation_type, self.to_article.title)

# class ArticleRights(db.Model):
    # user = ForeignKeyField(User)
    # article = ForiegnKeyField(Article)
    # right = ForiegnKeyField(UserRights)

# class UserRights(db.Model):
    # right = # owner, editor, reader

#        
#class Metadata(db.Model): # Metadata to any article
#    article = ForeignKeyField(Article)
#    key = CharField()
#    value = CharField()
#


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