from hashlib import md5
from auth import BaseUser
from misc import slugify, now
from raconteur import db
from flask.ext.mongoengine.wtf import model_form

'''
Created on 2 jan 2014

@author: Niklas
'''
    
# A user in the system
class User(db.Document, BaseUser):
    username = db.StringField(unique=True, max_length=60)
    password = db.StringField(max_length=60)
    email = db.EmailField(max_length=60) # TODO make into email field
    realname = db.StringField(max_length=60)
    location = db.StringField(max_length=60)
    description = db.StringField() # TODO should have a max length, but if we set it, won't be rendered as TextArea
    xp = db.IntField(default=0)
    join_date = db.DateTimeField(default=now())
    # msglog = db.ReferenceField(Conversation)
    active = db.BooleanField(default=True)
    admin = db.BooleanField(default=False)
    following = db.ListField(db.ReferenceField('self'))

    def __unicode__(self):
        return self.username

    def full_string(self):
        return "%s (%s)" % (self.username, self.realname)
     
    def log(self, msg):
        pass # TODO

    def groups(self):
        return Group.objects(members__user=self)

    def messages(self):
        return Message.objects(user=self).order_by('-pub_date')
        
    def get_most_recent_conversation_with(self, recipients):
        # A private conversation is one which is only between this user
        # and the given recipients, with no other users
        if not recipients:
            raise ValueError('Empty list of recipients')
        if not isinstance(recipients, list) or not isinstance(recipients[0], User):
            raise TypeError('Expects a list of User')
        print "recipients is list of %s, first item is %s" % (type(recipients[0]), recipients[0])
        recipients = recipients + [self]
        # All conversations where all recipients are present and the length of the lists are the same
        return Conversation.objects(members__all=recipients, members__size=len(recipients))

    def gravatar_url(self, size=48):
        return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' %\
               (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

    @classmethod
    def get_form(cls):
        return model_form(User, exclude=['password','admin', 'active', 'xp','username', 'join_date'])

    # @classmethod
    # def allowed(cls, user, op='view', instance=None):
    #     if user:
    #         if op=='view' or op=='new':
    #             return True
    #         else:
    #             return (user.id == instance.id) # requesting user and passed user instance has same ID - you can edit yourself
    #     return False

class Conversation(db.Document):
    modified_date = db.DateTimeField(default=now())
    members = db.ListField(db.ReferenceField(User))
    title = db.StringField(max_length=60)
    topic = db.StringField(max_length=60)
    
    meta = {'ordering': ['-modified_date']}

    def is_private(self):
        return (members and len(members)>1)

    def messages(self):
        return Message.objects(conversation=self)

    def last_message(self):
        return Message.objects(conversation=self).order_by('-pub_date').first() # first only or none
        
    def __unicode__(self):
        return u'conversation'

ROLE_TYPES = ('MASTER','MEMBER','INVITED')
class Member(db.EmbeddedDocument):
    user = db.ReferenceField(User)
    role = db.StringField(choices=ROLE_TYPES, default=ROLE_TYPES[2])

# A gamer group, e.g. people who regularly play together. Has game masters
# and players
GAME_GROUP, WORLD_GROUP, ARTICLE_GROUP = 1,2,3
GROUP_TYPES = ((GAME_GROUP, 'gamegroup'), 
               (WORLD_GROUP, 'worldgroup'), 
               (ARTICLE_GROUP, 'articlegroup'))
class Group(db.Document):
    name = db.StringField(max_length=60, required=True)
    location = db.StringField(max_length=60)
    slug = db.StringField()
    description = db.StringField() # TODO should have a max length, but if we set it, won't be rendered as TextArea
    type = db.IntField(choices=GROUP_TYPES,default=GAME_GROUP)
    members = db.ListField(db.EmbeddedDocumentField(Member))
    
    def __unicode__(self):
        return self.name

    def add_masters(self, new_masters):
        self.members.extend([Member(user=m,role='MASTER') for m in new_masters])

    def add_members(self, new_members):
        self.members.extend([Member(user=m,role='MEMBER') for m in new_members])

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super(Group, self).save(*args, **kwargs)

    def members_as_users(self):
        return [m for m.user in members]
        
# A message from a user (to everyone)
class Message(db.Document):
    user = db.ReferenceField(User)
    content = db.StringField()
    pub_date = db.DateTimeField(default=now())
    conversation = db.ReferenceField(Conversation)
    #readable_by = IntegerField(choices=((1, 'user'), (2, 'group'), (3, 'followers'), (4, 'all')))

    def __unicode__(self):
        return '%s: %s' % (self.user, self.content)

    def clean(self):
        if self.conversation:
            self.conversation.modified_date = self.pub_date
            self.conversation.save()