from flask import abort, request, redirect, url_for, render_template, flash, Blueprint, g
from raconteur import auth
from resource import ResourceHandler, ResourceAccessStrategy
from model.user import User, Group, Conversation, Message

social = Blueprint('social', __name__, template_folder='../templates/social')

user_handler = ResourceHandler(ResourceAccessStrategy(User, 'users', 'username'))
user_handler.register_urls(social)

group_strategy = ResourceAccessStrategy(Group, 'groups', 'slug')
group_handler = ResourceHandler(group_strategy)
group_handler.register_urls(social)

conversation_handler = ResourceHandler(ResourceAccessStrategy(Conversation, 'conversations'))
conversation_handler.register_urls(social)

message_handler = ResourceHandler(ResourceAccessStrategy(Message, 'messages', parent_strategy=conversation_handler.strategy))
message_handler.register_urls(social)

@social.route('/')
@auth.login_required
def index():
    following_messages = Message.objects(conversation=None, user__in=g.user.following).order_by('-pub_date')
    return render_template('social/base.html', following_message_list=following_messages)
