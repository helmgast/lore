from hashlib import md5, sha1
import datetime

from flask_peewee.auth import BaseUser
from peewee import *

from app import db
    
class User(db.Model, BaseUser):
    username = CharField()
    password = CharField()
    email = CharField()
    realname = CharField()
    join_date = DateTimeField(default=datetime.datetime.now)
    active = BooleanField(default=True)
    admin = BooleanField(default=False)

    def __unicode__(self):
        return self.username

    def following(self):
        return User.select().join(
            Relationship, on='to_user_id'
        ).where(from_user=self).order_by('username')

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
        return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
            (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

class Group(db.Model):
    name = CharField()
    location = CharField()
    
    def masters(self):
        return User.select().join(GroupMaster).where(group=self)
            
    def players(self):
        return User.select().join(GroupPlayer).where(group=self)
    
class GroupMaster(db.Model):
    group = ForeignKeyField(Group)
    master = ForeignKeyField(User)

class GroupPlayer(db.Model):
    group = ForeignKeyField(Group)
    player = ForeignKeyField(User)    

class Relationship(db.Model):
    from_user = ForeignKeyField(User, related_name='relationships')
    to_user = ForeignKeyField(User, related_name='related_to')
    
    def __unicode__(self):
        return 'Relationship from %s to %s' % (self.from_user, self.to_user)

class Message(db.Model):
    user = ForeignKeyField(User)
    content = TextField()
    pub_date = DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return '%s: %s' % (self.user, self.content)

class Note(db.Model):
    user = ForeignKeyField(User)
    message = TextField()
    status = IntegerField(choices=((1, 'live'), (2, 'deleted')), null=True)
    created_date = DateTimeField(default=datetime.datetime.now)
