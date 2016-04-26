"""
    controller.social
    ~~~~~~~~~~~~~~~~

    This is the controller and Flask blueprint for social features,
    it initializes URL routes based on the Resource module and specific
    ResourceRoutingStrategy for each related model class. This module is then
    responsible for taking incoming URL requests, parse their parameters,
    perform operations on the Model classes and then return responses via
    associated template files.

    :copyright: (c) 2014 by Helmgast AB
"""

from flask import abort, request, render_template, Blueprint, g, current_app
from flask.ext.classy import FlaskView
from flask.ext.mongoengine.wtf import model_form
from flask.ext.babel import lazy_gettext as _

from fablr.controller.resource import ResourceHandler, ResourceError, ResourceRoutingStrategy, RacBaseForm, \
    RacModelConverter, \
    ResourceAccessPolicy, Authorization
from fablr.model.user import User, Group, Member, Conversation, Message

social = Blueprint('social', __name__, template_folder='../templates/social')

user_form = model_form(User, base_class=RacBaseForm, converter=RacModelConverter(),
                       only=['username', 'realname', 'location', 'description'])


# user_form.confirm = PasswordField(_('Repeat Password'),
#   [validators.Required(), validators.Length(max=40)])
# user_form.password = PasswordField(_('New Password'), [
#   validators.Required(),
#   validators.EqualTo('confirm', message=_('Passwords must match')),
#   validators.Length(max=40)])

class UserAccessPolicy(ResourceAccessPolicy):
    def is_owner(self, op, instance):
        if g.user == instance:
            return Authorization(True, _("User %(user)s allowed to %(op)s on own user profile", user=g.user, op=op), privileged=True)
        else:
            return Authorization(False, _("Cannot access other user's user profile"))

user_access = UserAccessPolicy({
    'view': 'owner',
    'edit': 'owner',
    'form_edit': 'owner',
    '_default': 'admin'
})  # return user itself to check for owner of a user object

admin_only_access = ResourceAccessPolicy({'_default': 'admin'})

user_strategy = ResourceRoutingStrategy(User, 'users', 'id', form_class=user_form, access_policy=user_access)
ResourceHandler.register_urls(social, user_strategy)


class UsersView(FlaskView):
    def index(self):
        abort(501)  # Not implemented

    def get(self, id):
        abort(501)  # Not implemented

    def patch(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


class GroupsView(FlaskView):
    def index(self):
        abort(501)  # Not implemented

    def get(self, id):
        abort(501)  # Not implemented

    def patch(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


class MembersView(FlaskView):
    route_base = '/groups/<group>'

    def index(self):
        abort(501)  # Not implemented

    def get(self, id):
        abort(501)  # Not implemented

    def patch(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


class ConversationsView(FlaskView):
    def index(self):
        abort(501)  # Not implemented

    def get(self, id):
        abort(501)  # Not implemented

    def patch(self, id):
        abort(501)  # Not implemented

    def delete(self, id):
        abort(501)  # Not implemented


group_strategy = ResourceRoutingStrategy(Group, 'groups', 'slug', access_policy=admin_only_access)
ResourceHandler.register_urls(social, group_strategy)

member_strategy = ResourceRoutingStrategy(Member, 'members', None, parent_strategy=group_strategy)


class MemberHandler(ResourceHandler):
    def form_new(self, r):
        r = super(MemberHandler, self).form_new(r)
        # Remove existing member from the choice of new user in Member form
        current_member_ids = [m.user.id for m in r['group'].members]
        r['member_form'].user.queryset = r['member_form'].user.queryset.filter(id__nin=current_member_ids)
        return r

    def form_edit(self, r):
        r = super(MemberHandler, self).form_edit(r)
        current_member_ids = [m.user.id for m in r['group'].members]
        r['member_form'].user.queryset = r['member_form'].user.queryset.filter(id__nin=current_member_ids)
        return r


MemberHandler.register_urls(social, member_strategy)

conversation_strategy = ResourceRoutingStrategy(Conversation, 'conversations', access_policy=admin_only_access)


class ConversationHandler(ResourceHandler):
    def new(self, r):
        if not request.form.has_key('content') or len(request.form.get('content')) == 0:
            raise ResourceError(400, 'Need to attach first message with conversation')
        r = super(ConversationHandler, self).new(r)
        Message(content=request.form.get('content'), user=g.user, conversation=r['item']).save()
        return r

    def edit(self, r):
        r = super(ConversationHandler, self).edit(r)
        if request.form.has_key('content') and len(request.form.get('content')) > 0:
            Message(content=request.form.get('content'), user=g.user, conversation=r['item']).save()
        return r


ConversationHandler.register_urls(social, conversation_strategy)

message_strategy = ResourceRoutingStrategy(Message, 'messages', parent_strategy=conversation_strategy)
ResourceHandler.register_urls(social, message_strategy)


###
### Template filters
###
def is_following(from_user, to_user):
    return from_user.is_following(to_user)


social.add_app_template_filter(is_following)


@social.route('/')
@current_app.login_required
def index():
    following_messages = Message.objects(conversation=None, user__in=g.user.following).order_by('-pub_date')
    return render_template('social/_page.html', following_message_list=following_messages)
