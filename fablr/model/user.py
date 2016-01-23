"""
  model.user
  ~~~~~~~~~~~~~~~~

  Includes all Mongoengine model classes relating to social features,
  including the central User model, but also Conversation and Group.

  :copyright: (c) 2014 by Helmgast AB
"""

from hashlib import md5
from baseuser import BaseUser, make_password, create_token
from misc import now, Choices, slugify
from mongoengine import ValidationError
from flask.ext.mongoengine.wtf import model_form
from wtforms.fields import HiddenField
# i18n (Babel)
from flask.ext.babel import lazy_gettext as _
from flask.ext.mongoengine import Document # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, DateTimeField, FloatField, URLField, ImageField,
    ReferenceField, GenericReferenceField, BooleanField, ListField, IntField, EmailField, EmbeddedDocumentField)

import logging
from flask import current_app
logger = current_app.logger if current_app else logging.getLogger(__name__)

UserStatus = Choices(
  invited=_('Invited'),
  active=_('Active'),
  deleted=_('Deleted'))
ExternalAuth = Choices(
  google='Google',
  facebook='Facebook')

class ExternalAuth(EmbeddedDocument):
  id = StringField(required=True)
  long_token = StringField()
  emails = ListField(EmailField())

class UserEvent(EmbeddedDocument):
    created = DateTimeField(default=now())
    action = StringField()
    instance = GenericReferenceField()
    message = StringField()
    xp = IntField()

# A user in the system
class User(Document, BaseUser):
  # We want to set username unique, but then it cannot be empty,
  # but in case where username is created, we want to allow empty values
  # Currently it's only a display name, not used for URLs!
  username = StringField(max_length=60, verbose_name=_('Username'))
  password = StringField(max_length=60, verbose_name = _('Password'))
  email = EmailField(max_length=60, unique=True, min_length=6, verbose_name = _('Email'))
  realname = StringField(max_length=60, verbose_name = _('Real name'))
  location = StringField(max_length=60, verbose_name = _('Location'))
  description = StringField(verbose_name = _('Description'))  # TODO should have a max length, but if we set it, won't be rendered as TextArea
  xp = IntField(default=0, verbose_name = _('XP'))
  join_date = DateTimeField(default=now(), verbose_name = _('Join Date'))
  # msglog = ReferenceField(Conversation)
  status = StringField(choices=UserStatus.to_tuples(), default=UserStatus.invited, verbose_name=_('Status'))
  admin = BooleanField(default=False)
  newsletter = BooleanField(default=True)
  google_auth = EmbeddedDocumentField(ExternalAuth)
  facebook_auth = EmbeddedDocumentField(ExternalAuth)
  log = ListField(EmbeddedDocumentField(UserEvent))
  following = ListField(ReferenceField('self'), verbose_name = _('Following'))

  def clean(self):
    # TODO Our password hashes contain 46 characters, so we can check if the value
    # set is less, which means it's a user input that we need to hash before saving
    if self.password and len(self.password) <= 40:
      self.set_password(self.password)

  def display_name(self):
    return self.__unicode__()

  def __unicode__(self):
    return self.username if self.username else (
      self.realname.split(' ')[0] if self.realname else unicode(_('Anonymous')))

  def full_string(self):
    return "%s (%s)" % (self.username, self.realname)

  def log(self, action, instance, message='', metric=0):
    pass # TODO

  def create_token(self):
    return create_token(self.email)

  def auth_type(self):
    return "Google" if self.google_auth else "Facebook" if self.facebook_auth else _("Password") if self.password else _("No data")

  def groups(self):
    return Group.objects(members__user=self)

  def identifier(self):
    # TODO to also allow username here
    return self.id

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


class Conversation(Document):
  modified_date = DateTimeField(default=now())
  members = ListField(ReferenceField(User))
  title = StringField(max_length=60)
  topic = StringField(max_length=60)

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

MemberRoles = Choices(
  master=_('Master'),
  member=_('Member'),
  invited=_('Invited'))
class Member(EmbeddedDocument):
  user = ReferenceField(User)
  role = StringField(choices=MemberRoles.to_tuples(), default=MemberRoles.member)

  def get_role(self):
    return MemberRoles[self.role]

# A gamer group, e.g. people who regularly play together. Has game masters
# and players
GroupTypes = Choices(   gamegroup=_('Game Group'),
            worldgroup=_('World Group'),
            articlegroup=_('Article Group'))
class Group(Document):
  name = StringField(max_length=60, required=True)
  location = StringField(max_length=60)
  slug = StringField()
  description = StringField() # TODO should have a max length, but if we set it, won't be rendered as TextArea
  type = StringField(choices=GroupTypes.to_tuples(),default=GroupTypes.gamegroup)
  members = ListField(EmbeddedDocumentField(Member))

  def __unicode__(self):
    return self.name

  def add_masters(self, new_masters):
    self.members.extend([Member(user=m,role=MemberRoles.master) for m in new_masters])

  def add_members(self, new_members):
    self.members.extend([Member(user=m,role=MemberRoles.master) for m in new_members])

  def save(self, *args, **kwargs):
    self.slug = slugify(self.name)
    return super(Group, self).save(*args, **kwargs)

  def members_as_users(self):
    return [m for m.user in members]

# A message from a user (to everyone)
class Message(Document):
  user = ReferenceField(User)
  content = StringField()
  pub_date = DateTimeField(default=now())
  conversation = ReferenceField(Conversation)
  #readable_by = IntegerField(choices=((1, 'user'), (2, 'group'), (3, 'followers'), (4, 'all')))

  def __unicode__(self):
    return '%s: %s' % (self.user, self.content)

  def clean(self):
    if self.conversation:
      self.conversation.modified_date = self.pub_date
      self.conversation.save()
