from hashlib import md5
import datetime
from auth import BaseUser
from misc import slugify
from peewee import RawQuery
from raconteur import db
from flask.ext.mongoengine.wtf import model_form

'''
Created on 2 jan 2014

@author: Niklas
'''
class Conversation(db.Document):
    modified_date = db.DateTimeField(default=datetime.datetime.now)
    
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
class User(db.Document, BaseUser):
    username = db.StringField()
    password = db.StringField()
    email = db.StringField()
    realname = db.StringField()
    location = db.StringField()
    description = db.StringField()
    xp = db.IntField(default=0)
    join_date = db.DateTimeField(default=datetime.datetime.now)
    msglog = db.ReferenceField(Conversation)
    active = db.BooleanField(default=True)
    admin = db.BooleanField(default=False)

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

        param_marker = db.database_class.interpolation # in SQLite this is '?' but in Postgresql it's '%s'
        # We need to manually build a parameterized query, and the parameter marker is different for different underlying DB
        # We need a list of parameters representing member IDs, and we also need a count to match
        param_list = ','.join([param_marker for x in range(0,len(member_ids))])
        # Finally, we need to insert the individual parameters (the list of member ids plus total count) as an argument list,
        # using the * to unpack the resulting list
        rq = RawQuery(Conversation, 
            'SELECT c.id, c.modified_date FROM conversation c INNER JOIN conversationmember a ON a.conversation_id = c.id \
            WHERE a.member_id IN (%s) GROUP BY c.id, a.conversation_id, c.modified_date HAVING COUNT(*) = ( SELECT COUNT(*) FROM conversationmember b \
            WHERE b.conversation_id = a.conversation_id GROUP BY b.conversation_id) AND COUNT(*) = %s ORDER BY c.modified_date \
            DESC;' % (param_list, param_marker), *(member_ids+[len(member_ids)]))
        print param_marker, param_list, rq.sql()
        return rq

    def gravatar_url(self, size=48):
        return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' %\
               (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

    @classmethod
    def get_form(cls):
        return model_form(User, exclude=['password','admin', 'active', 'xp','username', 'join_date'])

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

class ConversationMember(db.Document):
    member = db.ReferenceField(User)
    conversation = db.ReferenceField(Conversation)

# A gamer group, e.g. people who regularly play together. Has game masters
# and players
GAME_GROUP, WORLD_GROUP, ARTICLE_GROUP = 1,2,3
class Group(db.Document):
    name = db.StringField()
    location = db.StringField()
    slug = db.StringField()
    description = db.StringField()
    type = db.IntField(choices=((GAME_GROUP, 'gamegroup'), (WORLD_GROUP, 'worldgroup'), (ARTICLE_GROUP, 'articlegroup')),default=GAME_GROUP)
    conversation = db.ReferenceField(Conversation)
    
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
class GroupMember(db.Document):
    group = db.ReferenceField(Group)
    member = db.ReferenceField(User)
    status = db.IntField(choices=((GROUP_MASTER, 'master'), (GROUP_PLAYER, 'player'), (GROUP_INVITED, 'invited')))
    
    def __unicode__(self):
        return "%s, %s in %s" % (self.member, self.status_text(), self.group)

    def save(self, *args, **kwargs):
        if self.member not in self.group.conversation.members():
            self.group.conversation.add_members([self.member])
        return super(GroupMember, self).save(*args, **kwargs)

    def status_text(self):
        return STATUSES[self.status]

# The directional relationship between two users, e.g. from_user follows to_user
class Relationship(db.Document):
    from_user = db.ReferenceField(User, related_name='relationships')
    to_user = db.ReferenceField(User, related_name='related_to')

    def __unicode__(self):
        return 'Relationship from %s to %s' % (self.from_user, self.to_user)
        
# A message from a user (to everyone)
class Message(db.Document):
    user = db.ReferenceField(User)
    content = db.StringField()
    pub_date = db.DateTimeField(default=datetime.datetime.now)
    conversation = db.ReferenceField(Conversation)
    #readable_by = IntegerField(choices=((1, 'user'), (2, 'group'), (3, 'followers'), (4, 'all')))

    def __unicode__(self):
        return '%s: %s' % (self.user, self.content)
  
