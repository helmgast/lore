"""
  model.user
  ~~~~~~~~~~~~~~~~

  Includes all Mongoengine model classes relating to social features,
  including the central User model, but also Conversation and Group.

  :copyright: (c) 2014 by Helmgast AB
"""
from __future__ import absolute_import
from datetime import datetime
from hashlib import md5

import math

from flask import flash

from .baseuser import BaseUser, create_token
from .misc import Choices, slugify, translate_action, datetime_delta_options, choice_options, from7to365, \
    numerical_options
from flask_babel import lazy_gettext as _
from .misc import Document  # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, DateTimeField, ReferenceField, GenericReferenceField,
                         BooleanField, ListField, IntField, EmailField, EmbeddedDocumentField, FloatField,
                         ValidationError, DoesNotExist, NULLIFY, DENY, CASCADE)

import logging
from flask import current_app

logger = current_app.logger if current_app else logging.getLogger(__name__)

UserStatus = Choices(
    invited=_('Invited'),
    active=_('Active'),
    deleted=_('Deleted'))

auth_services = {
    'google-oauth2': 'Google',
    'google': 'Google',
    'facebook': 'Facebook',
    'email': 'Email'
}


# TODO deprecate
class ExternalAuth(EmbeddedDocument):
    id = StringField(required=True)
    long_token = StringField()
    emails = ListField(EmailField())


# TODO deprecate
class UserEvent(EmbeddedDocument):
    created = DateTimeField(default=datetime.utcnow)
    action = StringField()
    instance = GenericReferenceField()
    message = StringField()
    xp = IntField()

    def action_string(self):
        try:
            return translate_action(self.action, self.instance)
        except DoesNotExist as dne:
            return self.action


# A user in the system
class User(Document, BaseUser):
    # meta = {
    #     'indexes': ['email', 'auth_keys']
    #
    #     # 'indexes': ['email', 'auth_keys.email']
    # }
    # ripperdoc@gmail.com|facebook|507316539704
    # We want to set username unique, but then it cannot be empty,
    # but in case where username is created, we want to allow empty values
    # Currently it's only a display name, not used for URLs!
    username = StringField(max_length=60, verbose_name=_('Username'))
    email = EmailField(max_length=60, unique=True, min_length=6, verbose_name=_('Contact Email'))
    auth_keys = ListField(StringField(max_length=100, unique=True), verbose_name=_('Authentication sources'))
    realname = StringField(max_length=60, verbose_name=_('Real name'))
    location = StringField(max_length=60, verbose_name=_('Location'))
    description = StringField(max_length=500, verbose_name=_('Description'))
    xp = IntField(default=0, verbose_name=_('XP'))
    join_date = DateTimeField(default=datetime.utcnow, verbose_name=_('Join Date'))
    last_login = DateTimeField(verbose_name=_('Last login'))
    status = StringField(choices=UserStatus.to_tuples(), default=UserStatus.invited, verbose_name=_('Status'))
    hidden = BooleanField(default=False)
    admin = BooleanField(default=False)
    logged_in = BooleanField(default=False)
    tourdone = BooleanField(default=False)
    avatar_url = StringField(verbose_name=_('Avatar URL'))

    # Uses string instead of Class to avoid circular import
    publishers_newsletters = ListField(ReferenceField('Publisher'))  # Reverse delete rule in world.py
    world_newsletters = ListField(ReferenceField('World'))  # Reverse delete rule in world.py
    images = ListField(ReferenceField('FileAsset'), verbose_name=_('Images'))  # Reverse delete rule in asset.py
    following = ListField(ReferenceField('self', reverse_delete_rule=NULLIFY), verbose_name=_('Following'))

    # TODO deprecate
    password = StringField(max_length=60, verbose_name=_('Password'))
    newsletter = BooleanField(default=True, verbose_name=_('Accepting newsletters'))
    google_auth = EmbeddedDocumentField(ExternalAuth)
    facebook_auth = EmbeddedDocumentField(ExternalAuth)
    event_log = ListField(EmbeddedDocumentField(UserEvent))

    def clean(self):
        # if self.username and self.location and self.description and self.images:
        #     # Profile is completed
        #     self.log(action='completed_profile', resource=self)  # metric is 1
        try:
            self.recalculate_xp()
        except ValidationError as ve:
            # May come if we try to count objects referring to this user, while the user hasn't been created yet
            pass

    def recalculate_xp(self):
        xp = Event.objects(user=self).sum('xp')
        if xp != self.xp:
            self.xp = xp
            return True
        return False

    def enumerate_auth_keys(self):
        # Assumes a Auth0 auth_id prepended with an email, e.g email@domain.com|email|58ba793c0bdcab0a0ec46cf7
        if not self.auth_keys:
            return
        else:
            for key in self.auth_keys:
                split_key = key.split('|')
                if not len(split_key) == 3 or any(not k for k in split_key):
                    raise ValidationError("Auth key {key} is not valid".format(key=key))
                else:
                    yield split_key

    def display_name(self):
        return self.realname or self.username or self.email.split('@')[0]

    def __str__(self):
        return self.display_name()

    def full_string(self):
        return u"%s (%s)" % (self.username, self.realname)

    def log(self, action, resource, message='', metric=1.0):
        ev = Event(user=self, action=action, resource=resource, message=message, metric=metric)
        ev.save()
        return ev.xp

    def create_token(self):
        return create_token(self.email)

    def auth_type(self):
        return "Google" if self.google_auth else "Facebook" if self.facebook_auth else _(
            "Password") if self.password else _("No data")

    def groups(self):
        return Group.objects(members__user=self)

    def identifier(self):
        # TODO to also allow username here
        return self.id

    def gravatar_url(self, size=48):
        return '//www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
               (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

    # TODO hack to avoid bug in https://github.com/MongoEngine/mongoengine/issues/1279
    def get_field_display(self, field):
        return self._BaseDocument__get_field_display(self._fields[field])


User.status.filter_options = choice_options('status', User.status.choices)
User.last_login.filter_options = datetime_delta_options('last_login', from7to365)
User.join_date.filter_options = datetime_delta_options('join_date', from7to365)
User.xp.filter_options = numerical_options('xp', [0, 50, 100, 200])


class Event(Document):
    meta = {
        'ordering': ['-created']
    }

    action = StringField(required=True, max_length=62, unique_with=(['created', 'user']))  # URL-friendly name
    created = DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
    user = ReferenceField(User, reverse_delete_rule=NULLIFY, verbose_name=_('User'))
    resource = GenericReferenceField(verbose_name=_('Resource'))
    message = StringField(max_length=500, verbose_name=_('Message'))
    metric = FloatField(default=1.0, verbose_name=_('Metric'))
    xp = IntField(default=0, verbose_name=_('XP'))

    def clean(self):
        self.xp = Event.calculate_xp(self)

    def action_string(self):
        try:
            return translate_action(self.action, self.resource)
        except DoesNotExist as dne:
            return self.action

    @staticmethod
    def calculate_xp(event):
        if event.action in xp_actions:
            count = len(Event.objects(user=event.user, action=event.action)) + 1
            if is_power(count, xp_actions[event.action]['base']):
                xp = xp_actions[event.action]['func'](event.metric)
                if xp:
                    flash(_('%(action)s: %(xp)s XP awarded to %(user)s', action=event.action_string(), xp=xp,
                            user=event.user, ), 'info')
                return xp
        return 0


# When we add an Event, we check below formulas for XP per metric.
# However, we need to throttle new XP, which we do by counting number of same action from same user before
# We do this with an exponential period, which means we award XP with an ever-growing interval. Different XP actions
# can have a different base value:
#  base=0: only first event will ever count
#  base=1: every event will count
#  base=2: 1st, 2nd, 4th, 8th, etc event will count
#  base=3: and so on
# We can count these events throughout all history or for a limited time period, thus resetting the counter


xp_actions = {
    'patch': {'func': lambda x: int(5 * x), 'base': 2},  # Patched a resource
    'post': {'func': lambda x: int(10 * x), 'base': 2},  # Posted a new resource
    'get': {'func': lambda x: int(1 * x), 'base': 2},  # Visit a page
    'comment': {'func': lambda x: int(3 * x), 'base': 2},  # Posted a disqus comment (TBD)
    'completed_profile': {'func': lambda x: int(10 * x), 'base': 0},  # Completed profile
    'purchase': {'func': lambda x: int(x), 'base': 1},  # 1 per SEK, with fixed FX
    'share': {'func': lambda x: int(3 * x), 'base': 2},  # Initiate a share on Facebook etc (TBD)
    'deed': {'func': lambda x: int(50 * x), 'base': 1},  # A heroic deed, as judged by an admin
}


def is_power(num, base):
    if base == 1: return True
    if base == 0: return num == 1
    if base < 0: return False
    return base ** int(math.log(num, base) + .5) == num


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
GroupTypes = Choices(gamegroup=_('Game Group'),
                     worldgroup=_('World Group'),
                     articlegroup=_('Article Group'),
                     newsletter=_('Newsletter'))


class Group(Document):
    slug = StringField(unique=True, max_length=62)  # URL-friendly name
    title = StringField(max_length=60, required=True, verbose_name=_('Title'))
    description = StringField(max_length=500, verbose_name=_('Description'))
    created = DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
    updated = DateTimeField(default=datetime.utcnow, verbose_name=_('Updated'))
    location = StringField(max_length=60)
    type = StringField(choices=GroupTypes.to_tuples(), default=GroupTypes.gamegroup)

    images = ListField(ReferenceField('FileAsset'), verbose_name=_('Images'))  # Reverse delete rule in asset.py
    members = ListField(EmbeddedDocumentField(Member))

    def __str__(self):
        return self.title or u''

    def add_masters(self, new_masters):
        self.members.extend([Member(user=m, role=MemberRoles.master) for m in new_masters])

    def add_members(self, new_members):
        self.members.extend([Member(user=m, role=MemberRoles.master) for m in new_members])

    def clean(self):
        self.updated = datetime.utcnow()
        self.slug = slugify(self.title)

    def members_as_users(self):
        return [m.user for m in self.members]

    # TODO hack to avoid bug in https://github.com/MongoEngine/mongoengine/issues/1279
    def get_field_display(self, field):
        return self._BaseDocument__get_field_display(self._fields[field])


Group.type.filter_options = choice_options('type', Group.type.choices)
Group.created.filter_options = datetime_delta_options('created', from7to365)
Group.updated.filter_options = datetime_delta_options('updated', from7to365)
