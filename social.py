from flask_peewee.utils import object_list, get_object_or_404
from flask import request, redirect, url_for, render_template, flash, Blueprint
from auth import auth
from models import *

def create_tables():
    User.create_table(fail_silently=True)
    Relationship.create_table(fail_silently=True)
    Message.create_table(fail_silently=True)
    Note.create_table(fail_silently=True)
    Group.create_table(fail_silently=True)
    GroupMaster.create_table(fail_silently=True)
    GroupPlayer.create_table(fail_silently=True)

social = Blueprint('social', __name__, template_folder='templates')

@social.route('/')
@auth.login_required
def index():
    user = auth.get_logged_in_user()
    messages = Message.select().where(
        user__in=user.following()
    ).order_by(('pub_date', 'desc'))
    print messages
    return object_list('social/social.html', messages, 'message_list')

@social.route('/public/')
def public_timeline():
    messages = Message.select().order_by(('pub_date', 'desc'))
    return object_list('social/public_messages.html', messages, 'message_list')

@social.route('/following/')
@auth.login_required
def following():
    user = auth.get_logged_in_user()
    return object_list('social/user_following.html', user.following(), 'user_list')

@social.route('/followers/')
@auth.login_required
def followers():
    user = auth.get_logged_in_user()
    return object_list('social/user_followers.html', user.followers(), 'user_list')

@social.route('/users/')
def user_list():
    users = User.select().order_by('username')
    return object_list('social/all_users.html', users, 'user_list')

@social.route('/users/<username>/')
def user_detail(username):
    user = get_object_or_404(User, username=username)
    messages = user.message_set.order_by(('pub_date', 'desc'))
    return object_list('social/user_detail.html', messages, 'message_list', person=user)

@social.route('/users/<username>/follow/', methods=['POST'])
@auth.login_required
def user_follow(username):
    user = get_object_or_404(User, username=username)
    Relationship.get_or_create(
        from_user=auth.get_logged_in_user(),
        to_user=user,
    )
    flash('You are now following %s' % user.username)
    return redirect(url_for('user_detail', username=user.username))

@social.route('/users/<username>/unfollow/', methods=['POST'])
@auth.login_required
def user_unfollow(username):
    user = get_object_or_404(User, username=username)
    Relationship.delete().where(
        from_user=auth.get_logged_in_user(),
        to_user=user,
    ).execute()
    flash('You are no longer following %s' % user.username)
    return redirect(url_for('user_detail', username=user.username))

@social.route('/create/', methods=['GET', 'POST'])
@auth.login_required
def create():
    user = auth.get_logged_in_user()
    if request.method == 'POST' and request.form['content']:
        message = Message.create(
            user=user,
            content=request.form['content'],
        )
        flash('Your message has been created')
        return redirect(url_for('user_detail', username=user.username))

    return render_template('social/create.html')