"""
  model.user
  ~~~~~~~~~~~~~~~~

  Includes all Mongoengine model classes relating to social features,
  including the central User model, but also Conversation and Group.

  :copyright: (c) 2014 by Helmgast AB
"""
from datetime import datetime
from hashlib import md5

import math
import re

from flask import flash, request

from .baseuser import BaseUser, create_token
from .misc import (
    Choices,
    slugify,
    translate_action,
    datetime_delta_options,
    choice_options,
    from7to365,
    numerical_options,
)
from flask_babel import lazy_gettext as _
from .misc import Document  # Enhanced document
from mongoengine import (
    EmbeddedDocument,
    StringField,
    DateTimeField,
    ReferenceField,
    GenericReferenceField,
    BooleanField,
    ListField,
    IntField,
    URLField,
    DynamicField,
    EmailField,
    EmbeddedDocumentField,
    FloatField,
    ValidationError,
    DoesNotExist,
    NULLIFY,
    DENY,
    CASCADE,
    Q,
)

import logging
from flask import current_app
from mongoengine.fields import MapField
from lore.model.misc import get

logger = current_app.logger if current_app else logging.getLogger(__name__)

UserStatus = Choices(invited=_("Invited"), active=_("Active"), deleted=_("Deleted"))

auth_services = {"google-oauth2": "Google", "google": "Google", "facebook": "Facebook", "email": "One-Time Code"}


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
        except DoesNotExist:
            return self.action


# class UserNotice(EmbeddedDocument):
#   """Could be used to show messages when a user logs in"""
#     last_login = DateTimeField(verbose_name=_("Created"))
#     redirect_to = URLField(verbose_name=_("Redirect to"))
#     msg = StringField(max_length=60, verbose_name=_("Message"))


# A user in the system
class User(Document, BaseUser):
    meta = {
        "indexes": [
            "email",
            # 'identities.profileData.email', # Cannot index a dynamic field
            # {"fields": ["username",], # Does unique but not for null fields
            #     "unique": True,
            #     "partialFilterExpression": {
            #         "username": {"$type": "string"}
            #      }
            # },
        ]
    }
    # We want to set username unique, but then it cannot be empty,
    # but in case where username is created, we want to allow empty values
    # Currently it's only a display name, not used for URLs!
    username = StringField(max_length=60, null=True, verbose_name=_("Username"))
    email = EmailField(max_length=60, unique=True, min_length=6, verbose_name=_("Contact Email"))
    realname = StringField(max_length=60, verbose_name=_("Real name"))
    location = StringField(max_length=60, verbose_name=_("Location"))
    description = StringField(max_length=500, verbose_name=_("Description"))
    xp = IntField(default=0, verbose_name=_("XP"))
    join_date = DateTimeField(default=datetime.utcnow, verbose_name=_("Join Date"))
    last_login = DateTimeField(verbose_name=_("Last login"))
    status = StringField(choices=UserStatus.to_tuples(), default=UserStatus.invited, verbose_name=_("Status"))
    hidden = BooleanField(default=False)
    admin = BooleanField(default=False)
    logged_in = BooleanField(default=False)
    tourdone = BooleanField(default=False)
    avatar_url = URLField(verbose_name=_("Avatar URL"))

    # Structure of identities (coming from Auth0)
    # First identity lacks profileData but is implicity that of user.email
    # "identities" : [
    #     {
    #         "provider" : "google-oauth2",
    #         "user_id" : "101739805468412392797",
    #         "connection" : "google-oauth2",
    #         "isSocial" : true
    #     },
    #     {
    #         "profileData" : {
    #             "email" : "froejd@gmail.com",
    #             "email_verified" : true
    #         },
    #         "user_id" : "5c1facce50d832460364aad8",
    #         "provider" : "email",
    #         "connection" : "email",
    #         "isSocial" : false
    #     },
    identities = DynamicField()
    access_token = StringField()

    images = ListField(ReferenceField("FileAsset"), verbose_name=_("Images"))  # Reverse delete rule in asset.py
    following = ListField(ReferenceField("self", reverse_delete_rule=NULLIFY), verbose_name=_("Following"))

    # TODO deprecated
    publishers_newsletters = ListField(ReferenceField("Publisher"))  # Reverse delete rule in world.py
    world_newsletters = ListField(ReferenceField("World"))  # Reverse delete rule in world.py
    password = StringField(max_length=60, verbose_name=_("Password"))
    newsletter = BooleanField(default=False, verbose_name=_("Consent to newsletters"))
    google_auth = EmbeddedDocumentField(ExternalAuth)
    auth_keys = ListField(StringField(max_length=100, unique=True), verbose_name=_("Authentication sources"))
    facebook_auth = EmbeddedDocumentField(ExternalAuth)
    event_log = ListField(EmbeddedDocumentField(UserEvent))

    def merge_in_user(self, remove_user):
        from lore.model.shop import Order  # Do here to avoid circular import

        changed_orders = Order.objects(user=remove_user).update(multi=True, user=self)
        changed_events = Event.objects(user=remove_user).update(multi=True, user=self)
        if remove_user.description and not self.description:
            self.description = remove_user.description
        if remove_user.realname and not self.realname:
            self.realname = remove_user.realname
        if remove_user.location and not self.location:
            self.location = remove_user.location
        if remove_user.join_date and remove_user.join_date < self.join_date:
            self.join_date = remove_user.join_date
        remove_user.status = "deleted"
        remove_user.identities = None
        remove_user.save()
        msg = (
            f"User '{self.email}' ({self.id}) merged in user '{remove_user.email}' ({remove_user.id}), moving "
            + f"{changed_orders} orders and {changed_events} events"
        )
        logger.warning(msg)
        # keep_user will be saved when we return out of this func

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
        xp = Event.objects(user=self).sum("xp")
        if xp != self.xp:
            self.xp = xp
            return True
        return False

    # def enumerate_auth_keys(self):
    #     # Assumes a Auth0 auth_id prepended with an email, e.g email@domain.com|email|58ba793c0bdcab0a0ec46cf7
    #     if not self.auth_keys:
    #         return
    #     else:
    #         for key in self.auth_keys:
    #             split_key = key.split('|')
    #             if not len(split_key) == 3 or any(not k for k in split_key):
    #                 raise ValidationError("Auth key {key} is not valid".format(key=key))
    #             else:
    #                 yield split_key

    def display_name(self):
        return self.realname or self.username or self.email.split("@")[0]

    def __str__(self):
        return self.display_name()

    def full_string(self):
        return "%s (%s)" % (self.username, self.realname)

    def log(self, action, resource, message="", metric=1.0, created=None):
        ev = Event(user=self, action=action, resource=resource, message=message, metric=metric)
        if created is not None:
            ev.created = created
        ev.save()
        return ev.xp

    def identities_by_email(self):
        """Returns a dict with emails as keys and values as a list of providers linked to that email.

        Returns:
            [dict] -- emails mapped to providers
        """
        emails = {}
        if self.identities:
            for id in self.identities:
                if "profileData" in id and "email" in id["profileData"]:
                    emails.setdefault(id["profileData"]["email"], []).append(auth_services[id["provider"]])
                else:
                    emails.setdefault(self.email, []).append(auth_services[id["provider"]])
        else:  # If user has never logged in, identities would be empty
            emails = {self.email: "default"}
        return emails

    @staticmethod
    def query_user_by_email(email, return_deleted=False):
        """Authoritative method for finding existing user in database based on provided email.
        Looks for users that either have the main email, or have the email within their identities.
        We compare emails case-insensitively (froejd@ == FROEJD@) but always store main email as lowercase.
        Identities object from Auth0 MAY contain uppercase although unusual.
        """
        # Deprectated fields google_auth.emails and facebook_auth.emails are not searched as they in old data always are same as user.email
        # Deprecated field auth_keys shouldn't contain unique emails not in identities but haven't verified yet

        # q = User.objects(__raw__={"$or": [
        #     {"email":f"/^{email}$/i"}, # Match from start to end of string
        #     {"identities.profileData.email": f"/^{email}$/i"}, # Match from start to end of string
        #     {"auth_keys":f"/^{email}\|/i"} # Find from start to |
        # ]})
        part_q = (
            Q(email__iexact=email)
            | Q(__raw__={"identities.profileData.email": re.compile(f"^{email}$", re.IGNORECASE)})
            | Q(auth_keys__istartswith=email)
        )
        if not return_deleted:  # Remove deleted from results
            part_q = part_q & Q(status__ne="deleted")
        q = User.objects(part_q)
        return q

    def create_token(self):
        return create_token(self.email)

    def auth_type(self):
        return (
            "Google"
            if self.google_auth
            else "Facebook"
            if self.facebook_auth
            else _("Password")
            if self.password
            else _("No data")
        )

    def groups(self):
        return Group.objects(members__user=self)

    def identifier(self):
        # TODO to also allow username here
        return self.id

    def gravatar_url(self, size=48):
        return "//www.gravatar.com/avatar/%s?d=identicon&s=%d" % (
            md5(self.email.strip().lower().encode("utf-8")).hexdigest(),
            size,
        )


User.status.filter_options = choice_options("status", User.status.choices)
User.last_login.filter_options = datetime_delta_options("last_login", from7to365)
User.join_date.filter_options = datetime_delta_options("join_date", from7to365)
User.xp.filter_options = numerical_options("xp", [0, 50, 100, 200])


class Event(Document):
    meta = {"ordering": ["-created"]}

    action = StringField(required=True, max_length=62, unique_with=(["created", "user"]))  # URL-friendly name
    created = DateTimeField(default=datetime.utcnow, verbose_name=_("Created"))
    user = ReferenceField(User, reverse_delete_rule=NULLIFY, verbose_name=_("User"))
    resource = GenericReferenceField(verbose_name=_("Resource"))
    message = StringField(max_length=500, verbose_name=_("Message"))
    metric = FloatField(default=1.0, verbose_name=_("Metric"))
    xp = IntField(default=0, verbose_name=_("XP"))

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
            if is_power(count, xp_actions[event.action]["base"]):
                xp = xp_actions[event.action]["func"](event.metric)
                if xp and request:  # If request context, otherwise don't show flash
                    flash(
                        _(
                            "%(action)s: %(xp)s XP awarded to %(user)s",
                            action=event.action_string(),
                            xp=xp,
                            user=event.user,
                        ),
                        "info",
                    )
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
    "patch": {"func": lambda x: int(5 * x), "base": 2},  # Patched a resource
    "post": {"func": lambda x: int(10 * x), "base": 2},  # Posted a new resource
    "get": {"func": lambda x: int(1 * x), "base": 2},  # Visit a page
    "comment": {"func": lambda x: int(3 * x), "base": 2},  # Posted a disqus comment (TBD)
    "completed_profile": {"func": lambda x: int(10 * x), "base": 0},  # Completed profile
    "purchase": {"func": lambda x: int(x), "base": 1},  # 1 per SEK, with fixed FX
    "share": {"func": lambda x: int(3 * x), "base": 2},  # Initiate a share on Facebook etc (TBD)
    "deed": {"func": lambda x: int(50 * x), "base": 1},  # A heroic deed, as judged by an admin
}


def is_power(num, base):
    if base == 1:
        return True
    if base == 0:
        return num == 1
    if base < 0:
        return False
    return base ** int(math.log(num, base) + 0.5) == num


MemberRoles = Choices(master=_("Master"), member=_("Member"), invited=_("Invited"))


class Member(EmbeddedDocument):
    user = ReferenceField(User)
    role = StringField(choices=MemberRoles.to_tuples(), default=MemberRoles.member)

    def get_role(self):
        return MemberRoles[self.role]


# A gamer group, e.g. people who regularly play together. Has game masters
# and players
GroupTypes = Choices(
    gamegroup=_("Game Group"), worldgroup=_("World Group"), articlegroup=_("Article Group"), newsletter=_("Newsletter")
)


class Group(Document):
    slug = StringField(unique=True, max_length=62)  # URL-friendly name
    title = StringField(max_length=60, required=True, verbose_name=_("Title"))
    description = StringField(max_length=500, verbose_name=_("Description"))
    created = DateTimeField(default=datetime.utcnow, verbose_name=_("Created"))
    updated = DateTimeField(default=datetime.utcnow, verbose_name=_("Updated"))
    location = StringField(max_length=60)
    type = StringField(choices=GroupTypes.to_tuples(), default=GroupTypes.gamegroup)

    images = ListField(ReferenceField("FileAsset"), verbose_name=_("Images"))  # Reverse delete rule in asset.py
    members = ListField(EmbeddedDocumentField(Member))

    def __str__(self):
        return self.title or ""

    def add_masters(self, new_masters):
        self.members.extend([Member(user=m, role=MemberRoles.master) for m in new_masters])

    def add_members(self, new_members):
        self.members.extend([Member(user=m, role=MemberRoles.master) for m in new_members])

    def clean(self):
        self.updated = datetime.utcnow()
        self.slug = slugify(self.title)

    def members_as_users(self):
        return [m.user for m in self.members]


Group.type.filter_options = choice_options("type", Group.type.choices)
Group.created.filter_options = datetime_delta_options("created", from7to365)
Group.updated.filter_options = datetime_delta_options("updated", from7to365)


def user_from_email(*emails, realname="", create=False, commit=False):
    created = False
    user = None
    i = 0
    while user is None and i < len(emails):
        user = User.query_user_by_email(emails[i]).first()
        i += 1
    if create and not user:
        user = User(email=emails[0])
        if realname:
            user.realname = realname
        if commit:
            created = True
            user.save()
    return user, created


def import_user(job, data, commit=False, create=True, if_newer=True):
    email = get(data, "email", "").lower()
    if not email:
        if job:
            job.warn("Missing email from this import, can't proceed")
        return None

    user = User.query_user_by_email(email)
    if user:
        is_updating = True  # We are patching an existing object
        # There is an existing product
    elif create:
        if job:
            job.warn("New user, but we will currently not create new users")
        return None

    newsletter = get(data, "newsletter", None)
    if newsletter is not None:
        user.newsletter = bool(newsletter)

    if commit:
        user.save()

    return user
