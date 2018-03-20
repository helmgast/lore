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

from fablr.api.auth import get_logged_in_user
from fablr.api.resource import RacBaseForm, RacModelConverter, ResourceAccessPolicy, Authorization, ResourceView, \
    filterable_fields_parser, prefillable_fields_parser, ListResponse, ItemResponse
from fablr.extensions import csrf
from fablr.model.misc import EMPTY_ID, set_lang_options
from fablr.model.user import User, Group, Event
from fablr.model.world import Publisher

social = Blueprint('social', __name__)
logger = current_app.logger if current_app else logging.getLogger(__name__)


def filter_authorized():
    if not g.user:
        return Q(id=EMPTY_ID)
    return Q(id=g.user.id)


class UserAccessPolicy(ResourceAccessPolicy):
    def is_editor(self, op, user, res):
        if user == res:
            return Authorization(True, _("Allowed access to %(op)s %(res)s own user profile", op=op, res=res),
                                 privileged=True)
        else:
            return Authorization(False, _("Cannot access other user's user profile"))

    def is_reader(self, op, user, res):
        return self.is_editor(op, user, res)


FinishTourForm = model_form(User,
                            base_class=Form,  # No CSRF on this one
                            only=['tourdone'],
                            converter=RacModelConverter())


class UsersView(ResourceView):
    access_policy = UserAccessPolicy()
    subdomain = '<pub_host>'
    model = User
    list_template = 'social/user_list.html'
    list_arg_parser = filterable_fields_parser(['username', 'status', 'xp', 'location', 'join_date', 'last_login'])
    item_template = 'social/user_item.html'
    item_arg_parser = prefillable_fields_parser(['username', 'realname', 'location', 'description'])
    form_class = model_form(User,
                            base_class=RacBaseForm,
                            only=['username', 'realname', 'location', 'description', 'images'],
                            converter=RacModelConverter())

    def index(self):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        users = User.objects().order_by('-username')
        r = ListResponse(UsersView, [('users', users)])
        r.auth_or_abort()
        r.set_theme('publisher', publisher.theme if publisher else None)

        if not (g.user and g.user.admin):
            r.query = r.query.filter(filter_authorized())
        r.prepare_query()
        return r

    def get(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        user = None
        if id == 'post':
            r = ItemResponse(UsersView, [('user', None)], extra_args={'intent': 'post'})
            r.auth_or_abort(res=None)
        else:
            user = User.objects(id=id).get_or_404()  # get_or_404 handles exception if not a valid object ID
            r = ItemResponse(UsersView, [('user', user)])
            if not getattr(g, 'user', None):
                # Allow invited only user to see this page
                g.user = get_logged_in_user(require_active=False)
            r.auth_or_abort()
        r.set_theme('publisher', publisher.theme if publisher else None)

        r.events = Event.objects(user=user) if user else []
        return r

    def patch(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        user = User.objects(id=id).get_or_404()  # get_or_404 handles exception if not a valid object ID
        r = ItemResponse(UsersView, [('user', user)], method='patch')

        if not getattr(g, 'user', None):
            # Allow invited only user to see this page
            g.user = get_logged_in_user(require_active=False)
        r.auth_or_abort()
        r.set_theme('publisher', publisher.theme if publisher else None)

        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(user, list(request.form.keys()))  # only populate selected keys
        user.status = 'active'  # Ensure active user

        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('social.UsersView:get', id=user.id))

    @route('/finish_tour', methods=['PATCH', 'GET'])
    @csrf.exempt
    def finish_tour(self):
        user = g.user
        if not user:
            logger.warning(_("No user to finish tour for"))
            abort(404)

        r = ItemResponse(UsersView, [('user', user)], method='patch', form_class=FinishTourForm)
        r.auth_or_abort()

        user.tourdone = True
        user.save()
        return r

    def post(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


UsersView.register_with_access(social, 'user')


class GroupsView(ResourceView):
    access_policy = UserAccessPolicy()
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
        r.auth_or_abort(res=None)
        r.prepare_query()
        return r

    def get(self, id):
        if id == 'post':
            r = ItemResponse(GroupsView, [('group', None)], extra_args={'intent': 'post'})
            r.auth_or_abort(res=None)
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
        r.form.populate_obj(group, list(request.form.keys()))  # only populate selected keys
        try:
            r.commit()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('social.GroupsView:get', id=group.slug))

    def post(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


# GroupsView.register_with_access(social, 'group')

social.add_url_rule('/', endpoint='social_home', redirect_to='/social/users/')
