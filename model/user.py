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
from misc import now, Choices
from raconteur import db
from mongoengine import ValidationError
from flask.ext.mongoengine.wtf import model_form
# i18n (Babel)
from flask.ext.babel import lazy_gettext as _

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


# A user in the system
class User(db.Document, BaseUser):
  # We want to set username unique, but then it cannot be empty, 
  # but in case where username is created, we want to allow empty values
  username = db.StringField(max_length=60, verbose_name=_('username'))
  password = db.StringField(max_length=60, min_length=8, verbose_name = _('password'))
  email = db.EmailField(max_length=60, required=True, min_length=6, verbose_name = _('email'))
  realname = db.StringField(max_length=60, verbose_name = _('real name'))
  location = db.StringField(max_length=60, verbose_name = _('location'))
  description = db.StringField(verbose_name = _('description'))  # TODO should have a max length, but if we set it, won't be rendered as TextArea
  xp = db.IntField(default=0, verbose_name = _('xp'))
  join_date = db.DateTimeField(default=now(), verbose_name = _('join date'))
  # msglog = db.ReferenceField(Conversation)
  status = db.StringField(choices=UserStatus.to_tuples(), default=UserStatus.invited, verbose_name=_('Status'))
  admin = db.BooleanField(default=False)
  external_access_token = db.StringField()
  external_id = db.StringField()
  external_service = db.StringField(choices=ExternalAuth.to_tuples())

  following = db.ListField(db.ReferenceField('self'), verbose_name = _('Following'))

  def clean(self):
    # Our password hashes contain 46 characters, so we can check if the value
    # set is less, which means it's a user input that we need to hash before saving
    if len(self.password) <= 40:
      self.password = make_password(self.password)
    if self.username and User.objects(username=self.username).only('username').first():
      raise ValidationError('Username %s is not unique' % self.username)

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

  def identifier(self):
    return self.username if self.username else self._id

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

MemberRoles = Choices(
  master=_('Master'), 
  member=_('Member'),
  invited=_('Invited'))
class Member(db.EmbeddedDocument):
  user = db.ReferenceField(User)
  role = db.StringField(choices=MemberRoles.to_tuples(), default=MemberRoles.member)

  def get_role(self):
    return MemberRoles[self.role]

# A gamer group, e.g. people who regularly play together. Has game masters
# and players
GroupTypes = Choices(   gamegroup=_('Game Group'), 
            worldgroup=_('World Group'), 
            articlegroup=_('Article Group'))
class Group(db.Document):
  name = db.StringField(max_length=60, required=True)
  location = db.StringField(max_length=60)
  slug = db.StringField()
  description = db.StringField() # TODO should have a max length, but if we set it, won't be rendered as TextArea
  type = db.StringField(choices=GroupTypes.to_tuples(),default=GroupTypes.gamegroup)
  members = db.ListField(db.EmbeddedDocumentField(Member))

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