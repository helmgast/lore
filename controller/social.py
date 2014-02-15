from flask import abort, request, redirect, url_for, render_template, flash, Blueprint, g
from raconteur import auth
from resource import ResourceHandler, ResourceError, ResourceAccessStrategy
from model.user import User, Group, Conversation, Message

social = Blueprint('social', __name__, template_folder='../templates/social')

user_strategy = ResourceAccessStrategy(User, 'users', 'username')
ResourceHandler.register_urls(social, user_strategy)

group_strategy = ResourceAccessStrategy(Group, 'groups', 'slug')
ResourceHandler.register_urls(social, group_strategy)

conversation_strategy = ResourceAccessStrategy(Conversation, 'conversations')

class ConversationHandler(ResourceHandler):
	def new(self, r):
		if not request.form.has_key('message'):
			raise ResourceError(400, 'Need to attach first message with conversation')
		r = super(ConversationHandler, self).new(r)
		Message.create(content=request.form.get('message'), user=g.user, conversation=r['item']).save()
		return r

ConversationHandler.register_urls(social, conversation_strategy)

message_strategy = ResourceAccessStrategy(Message, 'messages', parent_strategy=conversation_strategy)
ResourceHandler.register_urls(social, message_strategy)

@social.route('/')
@auth.login_required
def index():
    following_messages = Message.objects(conversation=None, user__in=g.user.following).order_by('-pub_date')
    return render_template('social/base.html', following_message_list=following_messages)
