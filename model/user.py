"""
    model.user
    ~~~~~~~~~~~~~~~~

    Includes all Mongoengine model classes relating to social features,
    including the central User model, but also Conversation and Group.

    :copyright: (c) 2014 by Raconteur
"""

from hashlib import md5
from auth import BaseUser, make_password, create_token
from slugify import slugify
from misc import now
from model.misc import list_to_choices
from raconteur import db
from flask.ext.mongoengine.wtf import model_form
# i18n (Babel)
from flask.ext.babel import lazy_gettext as _

import logging
from flask import current_app
logger = current_app.logger if current_app else logging.getLogger(__name__)

USER_STATUS = list_to_choices([
  'Invited', 
  'Active', 
  'Deleted'
  ])

# A user in the system
class User(db.Document, BaseUser):
    username = db.StringField(unique=True, max_length=60, min_length=6)
    password = db.StringField(max_length=60, min_length=8)
    email = db.EmailField(max_length=60, min_length=6)
    realname = db.StringField(max_length=60)
    location = db.StringField(max_length=60)
    description = db.StringField()  # TODO should have a max length, but if we set it, won't be rendered as TextArea
    xp = db.IntField(default=0)
    join_date = db.DateTimeField(default=now())
    # msglog = db.ReferenceField(Conversation)
    status = db.StringField(choices=USER_STATUS, default='invited', verbose_name=_('Status'))
    admin = db.BooleanField(default=False)
    following = db.ListField(db.ReferenceField('self'))

    #i18n
    username.verbose_name = _('username')
    password.verbose_name = _('password')
    email.verbose_name = _('email')
    realname.verbose_name = _('real name')
    location.verbose_name = _('location')
    description.verbose_name = _('description')
    xp.verbose_name = _('xp')
    join_date.verbose_name = _('join date')

    def clean(self):
    # Our password hashes contain 46 characters, so we can check if the value
    # set is less, which means it's a user input that we need to hash before saving
        if len(self.password) <= 40:
            self.password = make_password(self.password)

    def __unicode__(self):
        return self.username

    def full_string(self):
        return "%s (%s)" % (self.username, self.realname)

    def log(self, msg):
        pass # TODO

    def create_token(self):
        return create_token(self.email)

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
        logger.info("recipients is list of %s, first item is %s", type(recipients[0]), recipients[0])
        recipients = recipients + [self]
        # All conversations where all recipients are present and the length of the lists are the same
        return Conversation.objects(members__all=recipients, members__size=len(recipients))

    def gravatar_url(self, size=48):
        return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' %\
               (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

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

    members.verbose_name  = _('members')
    title.verbose_name  = _('title')
    topic.verbose_name  = _('topic')

    meta = {'ordering': ['-modified_date']}

    def is_private(self):
        return (members and len(members)>1)

    def messages(self):
        return Message.objects(conversation=self)

    def last_message(self):
        return Message.objects(conversation=self).order_by('-pub_date').first() # first only or none

    def __unicode__(self):
        return u'conversation'

MASTER, MEMBER, INVITED = 0,1,2
ROLE_TYPES = ((MASTER, _('MASTER')),(MEMBER, _('MEMBER')),(INVITED, _('INVITED')))
class Member(db.EmbeddedDocument):
    user = db.ReferenceField(User)
    role = db.IntField(choices=ROLE_TYPES, default=MEMBER)

    def get_role(self):
        return ROLE_TYPES[self.role][1]

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
        self.members.extend([Member(user=m,role=MASTER) for m in new_masters])

    def add_members(self, new_members):
        self.members.extend([Member(user=m,role=MEMBER) for m in new_members])

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