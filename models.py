from hashlib import md5
import datetime
from wtfpeewee.orm import model_form
from flask_peewee.auth import BaseUser
from flask_peewee.utils import slugify
from peewee import *

from app import db

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

# A user in the system
class User(db.Model, BaseUser):
    username = CharField()
    password = CharField()
    email = CharField()
    realname = CharField()
    location = CharField(null=True)
    join_date = DateTimeField(default=datetime.datetime.now)
    active = BooleanField(default=True)
    admin = BooleanField(default=False)

    def __unicode__(self):
        return self.username

    def full_string(self):
        return "%s (%s)" % (self.username, self.realname)
        
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
    
    def get_or_create_conversation_with(self, recipients):
        conversation_query = self.get_conversations_with(recipients)
        # Pick only one, and the most recent, in case there are many
        conversation_query = conversation_query.order_by(('modified_date','desc')).paginate(1,1)
        print conversation_query.sql()
        convs = [c for c in conversation_query]
        if not convs: # empty list
            conversation = Conversation.create()
            print "New conversation %i" % (conversation.id)
            members = [self]+recipients # merge lists
            conversation.add_members(members)
        else:
            conversation = convs[0]
        return conversation
        
    def get_conversations_with(self, recipients):
        # A private conversation is one which is only between this user
        # and the given recipients, with no other users
        if not recipients:
            raise ValueError('Empty list of recipients')
        if not isinstance(recipients, list) or not isinstance(recipients[0], User):
            raise TypeError('Expects a list of User')
        print "recipients is list of %s, first item is %s" % (type(recipients[0]), recipients[0])
        member_ids = [self.id]+[i.id for i in recipients]

        # Select Conversation first because we ultimately want to return a Conversation object
        # But we want to join it with Conversation members and only pick those where
        # the conversation has either this user or the defined recipient in the conversation
        sq = Conversation.select().join(ConversationMembers).where(member__in=member_ids)
        # However, that will give us conversations which may have just one or some of the
        # recipients. We ONLY want those conversations where all and
        # only all are members, so we group by and count members in the conversation
        sq = sq.group_by('conversation_id').having('count(member_id) = %i' % len(member_ids))
        # Resulting SQL query is:
        # SELECT t1."id", t1."modified_date" FROM "conversation" AS t1 INNER JOIN "conversationmembers"
        # AS t2 ON t1."id" = t2."conversation_id" WHERE t2."member_id" IN (?,?)
        # GROUP BY t2."conversation_id" HAVING count(member_id) = 2
        return sq

    def gravatar_url(self, size=48):
        return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' %\
               (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

class Conversation(db.Model):
    #creator = ForeignKeyField(User)
    modified_date = DateTimeField(default=datetime.datetime.now)
    
    def members(self):
        return User.select().join(ConversationMembers).where(conversation=self)
        
    def last_message(self):
        msgs = list(Message.select().where(conversation=self).order_by(('pub_date', 'desc')).limit(1))
        if len(msgs)==0:
            return None
        return msgs[0]
        
    def add_members(self, members):
        for m in members:
            cm = ConversationMembers.create(member=m, conversation=self)
            print "Created conversation member with member %s and conv %s" % (m.id, self.id)
        
class ConversationMembers(db.Model):
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
        self.conversation = Conversation.create()
        return super(Group, self).save(*args, **kwargs)
    
    def masters(self):
        return User.select().join(GroupMember).where(group=self,status=GROUP_MASTER)
    def players(self):
        return User.select().join(GroupMember).where(group=self,status=GROUP_PLAYER)
    def invited(self):
        return User.select().join(GroupMember).where(group=self,status=GROUP_INVITED)
    def members(self):
        return GroupMember.select().where(group=self).order_by(('status', 'asc'))

    def addMembers(self, newmembers, type):
        if not newmembers or not isinstance(newmembers[0], User):
            raise TypeError("Need a list of Users, got %s of type %s" % (newmembers, type(newmembers)))
        if not type in STATUSES.keys():
            raise TypeError("type need to be one predefined integers, see models.py")
        members_dict = dict([[gm.member.id,gm] for gm in GroupMember.select().where(group=self)])
        edited = []
        for u in newmembers:
            if u.id in members_dict:
                if type==GROUP_MASTER and members_dict[u].status == GROUP_PLAYER:
                    members_dict[u].status = GROUP_MASTER
                    edited.append(members_dict[u])
            else:
                edited.append(GroupMember.create(group=self, member=u, status=type))
        return edited

    def removeMembers(self, members):
        if not members or not isinstance(members[0], User):
            raise TypeError("Need a list of Users, got %s of type %s" % (members, type(members)))
        removed = []
        for gm in GroupMember.select().where(group=self,member__in=members):
            removed.append(gm)
            cm = ConversationMembers.get(conversation=self.conversation, member=gm.member)
            gm.delete_instance()
            cm.delete_instance() # Remove the user from the group conversation as well
        return removed
                
# An autogenerated form class for doing validation and POST / form processing
GroupForm = model_form(Group, exclude=['slug', 'conversation'])
        
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
        print self.group.conversation, self.group.conversation.members()
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
            
class GeneratorInputList(db.Model):
    name = CharField()

    def items(self):
        return GeneratorInputItem.select().where(input_list=self)

class GeneratorInputItem(db.Model):
    input_list = ForeignKeyField(GeneratorInputList)
    content = CharField()

class StringGenerator(db.Model):
    name = CharField()
    description = TextField()
    generator = None

    def __unicode__(self):
        return self.name


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