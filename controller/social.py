from flask import abort, request, redirect, url_for, render_template, flash, Blueprint, g
from raconteur import auth
from resource import ResourceHandler2, ResourceAccessStrategy
from model.user import User, Group, Conversation, Message

social = Blueprint('social', __name__, template_folder='../templates/social')

user_strategy = ResourceAccessStrategy(User, 'users', 'username')
ResourceHandler2.register_urls(social, user_strategy)

group_strategy = ResourceAccessStrategy(Group, 'groups', 'slug')
ResourceHandler2.register_urls(social, group_strategy)

conversation_strategy = ResourceAccessStrategy(Conversation, 'conversations')
ResourceHandler2.register_urls(social, conversation_strategy)

message_strategy = ResourceAccessStrategy(Message, 'messages', parent_strategy=conversation_strategy)
ResourceHandler2.register_urls(social, message_strategy)

@social.route('/')
@auth.login_required
def index():
    following_messages = Message.objects(conversation=None, user__in=g.user.following).order_by('-pub_date')
    return render_template('social/base.html', following_message_list=following_messages)
