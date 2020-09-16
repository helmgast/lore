"""
    controller.social
    ~~~~~~~~~~~~~~~~

    This is the controller and Flask blueprint for social features,
    This module is then responsible for taking incoming URL requests, parse their parameters,
    perform operations on the Model classes and then return responses via
    associated template files.

    :copyright: (c) 2016 by Helmgast AB
"""
import logging
from flask import abort, request, Blueprint, g, current_app
from flask import redirect
from flask import url_for
from flask_babel import lazy_gettext as _
from flask_classy import route
from flask_mongoengine.wtf import model_form
from mongoengine import NotUniqueError, ValidationError, Q
from wtforms import Form

from lore.api.auth import get_logged_in_user
from lore.api.resource import (
    Authorization,
    CheckboxListWidget,
    FilterableFields,
    HiddenModelField,
    ImprovedBaseForm,
    ImprovedModelConverter,
    ItemResponse,
    ListResponse,
    OrderedModelSelectMultipleField,
    ResourceAccessPolicy,
    ResourceView,
    filterable_fields_parser,
    prefillable_fields_parser,
)
from lore.extensions import csrf
from lore.model.misc import EMPTY_ID, set_lang_options
from lore.model.user import Event, Group, User
from lore.model.world import Publisher, World
from wtforms.fields.simple import BooleanField, HiddenField
from wtforms.widgets.core import CheckboxInput, HiddenInput, ListWidget
from wtforms.fields.core import SelectMultipleField
from flask_mongoengine.wtf.fields import ModelSelectField, ModelSelectMultipleField

social = Blueprint("social", __name__)
logger = current_app.logger if current_app else logging.getLogger(__name__)


def filter_authorized():
    if not g.user:
        return Q(id=EMPTY_ID)
    return Q(id=g.user.id)


class UserAccessPolicy(ResourceAccessPolicy):
    def authorize(self, op, user=None, res=None):
        # TODO temporary translation between old and new op words, e.g. patch vs edit
        op = self.translate.get(op, op)
        if not user:
            user = g.user

        if op == "list":
            return self.is_user(op, user, res)
        else:
            return super(UserAccessPolicy, self).authorize(op, user, res)

    def is_editor(self, op, user, res):
        if user == res:
            return Authorization(
                True, _("Allowed access to %(op)s %(res)s own user profile", op=op, res=res), privileged=True
            )
        else:
            return Authorization(False, _("Cannot access other user's user profile"))

    def is_reader(self, op, user, res):
        return self.is_editor(op, user, res)


FinishTourForm = model_form(
    User, base_class=Form, only=["tourdone"], converter=ImprovedModelConverter()  # No CSRF on this one
)


class UsersView(ResourceView):
    access_policy = UserAccessPolicy()
    subdomain = "<pub_host>"
    model = User
    list_template = "social/user_list.html"
    filterable_fields = FilterableFields(User, ["username", "status", "xp", "location", "join_date", "last_login"])
    item_template = "social/user_item.html"
    item_arg_parser = prefillable_fields_parser(["username", "realname", "location", "description"])

    # class ConsentForm(Form):
    #     publisher = HiddenModelField(model=Publisher, label=_("Publisher"))
    #     # interests = SelectMultipleField(label=_("Interests"), choices=[(0,"Eon"), (1, "Neotech"), (2, "Kult")])
    #     interests = OrderedModelSelectMultipleField(model=World, label=_("Interests"), widget=ListWidget(prefix_label=False), option_widget=CheckboxInput())
    #     consent = BooleanField(label=_("Consent"))

    # # Deep Nesting!! UserForm.follower_consents=ListField.EmbeddedDocumentField.interests=ListField.ReferenceField(World)
    # field_args = {
    #     "follow_consents": {  # Args for follow_consents ListField
    #         "field_args": {  # Args for FormField inside ListField
    #             "form_class": ConsentForm
    #         }
    #     }
    # }

    form_class = model_form(
        User,
        base_class=ImprovedBaseForm,
        only=["username", "realname", "location", "images", "newsletter", "avatar_url", "interests"],
        converter=ImprovedModelConverter(),
    )
    form_class.interests = ModelSelectMultipleField(
        model=World, label=_("Interests"), allow_blank=True, widget=CheckboxListWidget(), option_widget=CheckboxInput()
    )

    def index(self):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        users = User.objects().order_by("-username")
        r = ListResponse(UsersView, [("users", users)])
        r.auth_or_abort()
        r.set_theme("publisher", publisher.theme if publisher else None)

        if not (g.user and g.user.admin):
            r.query = r.query.filter(filter_authorized())
        r.finalize_query()
        return r

    def get(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        user = None
        if id == "post":
            r = ItemResponse(UsersView, [("user", None)], extra_args={"intent": "post"})
            r.auth_or_abort(res=None)
        else:
            # get_or_404 handles exception if not a valid object ID
            user = User.objects(id=id).get_or_404()

            # user.follow_consents.setdefault(publisher.id, FollowConsent())
            r = ItemResponse(UsersView, [("user", user)])
            if not getattr(g, "user", None):
                # Allow invited only user to see this page
                g.user = get_logged_in_user(require_active=False)
            r.auth_or_abort()
        r.set_theme("publisher", publisher.theme if publisher else None)

        r.events = Event.objects(user=user) if user else []
        return r

    def patch(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        # get_or_404 handles exception if not a valid object ID
        user = User.objects(id=id).get_or_404()
        r = ItemResponse(UsersView, [("user", user)], method="patch")

        if not getattr(g, "user", None):
            # Allow invited only user to see this page
            g.user = get_logged_in_user(require_active=False)
        r.auth_or_abort()
        r.set_theme("publisher", publisher.theme if publisher else None)

        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(user, list(request.form.keys()))  # only populate selected keys
        user.status = "active"  # Ensure active user

        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args["next"] or url_for("social.UsersView:get", id=user.id, intent="patch"))

    def post(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


UsersView.register_with_access(social, "user")


class GroupsView(ResourceView):
    access_policy = UserAccessPolicy()
    model = Group
    list_template = "social/group_list.html"
    filterable_fields = FilterableFields(Group, ["type", "location", "created", "updated"])
    item_template = "social/group_item.html"
    item_arg_parser = prefillable_fields_parser(["title", "location", "description"])
    form_class = model_form(
        Group, base_class=ImprovedBaseForm, exclude=["slug", "created", "updated"], converter=ImprovedModelConverter()
    )

    def index(self):
        groups = Group.objects().order_by("-updated")
        r = ListResponse(GroupsView, [("groups", groups)])
        r.auth_or_abort(res=None)
        r.finalize_query()
        return r

    def get(self, id):
        if id == "post":
            r = ItemResponse(GroupsView, [("group", None)], extra_args={"intent": "post"})
            r.auth_or_abort(res=None)
        else:
            group = Group.objects(slug=id).first_or_404()
            r = ItemResponse(GroupsView, [("group", group)])
            r.auth_or_abort()

        return r

    def patch(self, id):
        group = Group.objects(slug=id).first_or_404()
        r = ItemResponse(GroupsView, [("group", group)], method="patch")
        r.auth_or_abort()

        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        # only populate selected keys
        r.form.populate_obj(group, list(request.form.keys()))
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args["next"] or url_for("social.GroupsView:get", id=group.slug))

    def post(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


# GroupsView.register_with_access(social, 'group')
@social.route("/me", subdomain="<pub_host>")
def me():
    if g.user:
        return redirect(url_for("social.UsersView:get", intent="patch", id=g.user.identifier()))
    else:
        abort(401)  # Should redirect to sso


social.add_url_rule("/", endpoint="social_home", redirect_to="/social/users/")
