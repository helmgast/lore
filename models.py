from hashlib import md5
import datetime

from flask_peewee.auth import BaseUser
from peewee import *

from app import db

# A user in the system
class User(db.Model, BaseUser):
    username = CharField()
    password = CharField()
    email = CharField()
    realname = CharField()
    location = CharField()
    join_date = DateTimeField(default=datetime.datetime.now)
    active = BooleanField(default=True)
    admin = BooleanField(default=False)

    def __unicode__(self):
        return self.username

    # Users that this user follows
    def following(self):
        return User.select().join(
            Relationship, on='to_user_id'
        ).where(from_user=self).order_by('username')

    # Users that follows this user
    def followers(self):
        return User.select().join(
            Relationship, on='from_user_id'
        ).where(to_user=self).order_by('username')

    def is_following(self, user):
        return Relationship.filter(
            from_user=self,
            to_user=user
        ).exists()

    def master_in_groups(self):
        return Group.select().join(GroupMaster).where(master=self)

    def player_in_groups(self):
        return Group.select().join(GroupPlayer).where(player=self)

    def gravatar_url(self, size=48):
        return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' %\
               (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

# A gamer group, e.g. people who regularly play together. Has game masters
# and players
class Group(db.Model):
    name = CharField()
    location = CharField()

    def masters(self):
        return User.select().join(GroupMaster).where(group=self)

    def players(self):
        return User.select().join(GroupPlayer).where(group=self)

# The relationship between a user as a game master and a group
class GroupMaster(db.Model):
    group = ForeignKeyField(Group)
    master = ForeignKeyField(User)

# The relationship between a user as a player and group
class GroupPlayer(db.Model):
    group = ForeignKeyField(Group)
    player = ForeignKeyField(User)

# The directional relationship between two users, e.g. from_user follows to_user
class Relationship(db.Model):
    from_user = ForeignKeyField(User, related_name='relationships')
    to_user = ForeignKeyField(User, related_name='related_to')

    def __unicode__(self):
        return 'Relationship from %s to %s' % (self.from_user, self.to_user)

class Conversation(db.Model):
    #creator = ForeignKeyField(User)
    modified_date = DateTimeField(default=datetime.datetime.now)
    
    def members(self):
        return User.select().join(ConversationMembers).where(conversation=self)
        
    def last_message(self):
        return Message.select().where(conversation=self).order_by(('pub_date', 'desc')).limit(1)
        
class ConversationMembers(db.Model):
    member = ForeignKeyField(User)
    conversation = ForeignKeyField(Conversation)
        
# A message from a user (to everyone)
class Message(db.Model):
    user = ForeignKeyField(User)
    content = TextField()
    pub_date = DateTimeField(default=datetime.datetime.now)
    conversation = ForeignKeyField(Conversation)
    #readable_by = IntegerField(choices=((1, 'user'), (2, 'group'), (3, 'followers'), (4, 'all')))

    def __unicode__(self):
        return '%s: %s' % (self.user, self.content)
            
# All material related to a certain story.
class Campaign(db.Model):
    name = CharField()
    world = CharField() # The game world this belongs to
    group = ForeignKeyField(Group)
    rule_system = CharField()
    archived = BooleanField() # If the campaign is archived
    
# A part of a Scenario, that can be in current focus of a game
class Scene(db.Model):
    campaign = ForeignKeyField(Campaign)
    name = CharField()
    order = IntegerField() # The integer order between scenes
    act = CharField() # For larger scenarios, this scene belongs to which act
                
# A game session that was or will be held, e.g. the instance between a scenario
# and a group at a certain date
class Session(db.Model):
    play_start = DateTimeField()
    play_end = DateTimeField()
    campaign = ForeignKeyField(Campaign)
    location = CharField() # Location of the session

# Lists users present at a particular session
class SessionPresentUser(db.Model):
    present_user = ForeignKeyField(User)
    session = ForeignKeyField(Session)
            
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