"""
    controller.social
    ~~~~~~~~~~~~~~~~

    This is the controller and Flask blueprint for social features,
    This module is then responsible for taking incoming URL requests, parse their parameters,
    perform operations on the Model classes and then return responses via
    associated template files.

    :copyright: (c) 2016 by Helmgast AB
"""

from flask import abort, request, Blueprint, g
from flask import flash
from flask import redirect
from flask import url_for
from flask_babel import lazy_gettext as _
from flask_mongoengine.wtf import model_form
from mongoengine import NotUniqueError, ValidationError

from fablr.controller.resource import RacBaseForm, RacModelConverter, ResourceAccessPolicy, Authorization, ResourceView, \
    filterable_fields_parser, prefillable_fields_parser, ListResponse, ItemResponse
from fablr.model.user import User, Group, Event

social = Blueprint('social', __name__, template_folder='../templates/social')


class UserAccessPolicy(ResourceAccessPolicy):
    def is_owner(self, op, instance):
        if g.user == instance:
            return Authorization(True, _("User %(user)s allowed to %(op)s on own user profile", user=g.user, op=op),
                                 privileged=True)
        else:
            return Authorization(False, _("Cannot access other user's user profile"))


class UsersView(ResourceView):
    access_policy = UserAccessPolicy({
        'list': 'admin',
        'view': 'owner',
        'edit': 'owner',
        '_default': 'admin'
    })
    model = User
    list_template = 'social/user_list.html'
    list_arg_parser = filterable_fields_parser(['username', 'status', 'xp', 'location', 'join_date', 'last_login'])
    item_template = 'social/user_item.html'
    item_arg_parser = prefillable_fields_parser(['username', 'realname', 'location', 'description'])
    form_class = model_form(User,
                            base_class=RacBaseForm,
                            only=['username', 'realname', 'location', 'description'],
                            converter=RacModelConverter())

    def index(self):
        users = User.objects(status='active').order_by('-username')
        r = ListResponse(UsersView, [('users', users)])
        r.auth_or_abort()
        r.prepare_query()
        return r

    def get(self, id):
        if id == 'post':
            r = ItemResponse(UsersView, [('user', None)], extra_args={'intent': 'post'})
        else:
            user = User.objects(id=id).first_or_404()
            r = ItemResponse(UsersView, [('user', user)])
        r.events = Event.objects(user=user) if user else []
        r.auth_or_abort()
        return r

    def patch(self, id):
        user = User.objects(id=id).first_or_404()
        r = ItemResponse(UsersView, [('user', user)], method='patch')
        r.auth_or_abort()

        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(user, request.form.keys())  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('social.UsersView:get', id=user.id))

    def post(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


UsersView.register_with_access(social, 'user')


class GroupsView(ResourceView):
    access_policy = UserAccessPolicy({
        'list': 'admin',
        'view': 'admin',
        'edit': 'admin',
        '_default': 'admin'
    })
    model = Group
    list_template = 'social/group_list.html'
    list_arg_parser = filterable_fields_parser(['type', 'location', 'created', 'updated'])
    item_template = 'social/group_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'location', 'description'])
    form_class = model_form(Group,
                            base_class=RacBaseForm,
                            exclude=['slug', 'created', 'updated'],
                            converter=RacModelConverter())
    def index(self):
        groups = Group.objects().order_by('-updated')
        r = ListResponse(GroupsView, [('groups', groups)])
        r.auth_or_abort()
        r.prepare_query()
        return r

    def get(self, id):
        if id == 'post':
            r = ItemResponse(GroupsView, [('group', None)], extra_args={'intent': 'post'})
        else:
            group = Group.objects(slug=id).first_or_404()
            r = ItemResponse(GroupsView, [('group', group)])
        r.auth_or_abort()
        return r

    def patch(self, id):
        group = Group.objects(slug=id).first_or_404()
        r = ItemResponse(GroupsView, [('group', group)], method='patch')
        r.auth_or_abort()

        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(group, request.form.keys())  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('social.GroupsView:get', id=group.slug))

    def post(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented

GroupsView.register_with_access(social, 'group')

social.add_url_rule('/', endpoint='social_home', redirect_to='/social/users/')
