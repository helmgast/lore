"""
    fablr.auth
    ~~~~~~~~~~~~~~~~

   Authentication module that provides login and logout features on top of
   User model, uses Auth0.com as authentication backend.

    :copyright: (c) 2016 by Helmgast AB
"""

import functools
import json
from datetime import datetime

import requests

from flask import Blueprint, request, session, flash
from flask import abort
from flask import current_app
from flask import logging
from flask import redirect, url_for, g
from flask_babel import lazy_gettext as _

from fablr.controller.resource import re_next
from fablr.model.user import User

logger = current_app.logger if current_app else logging.getLogger(__name__)

auth_app = Blueprint('auth', __name__, template_folder='../templates/auth')

COOKIE_VERSION = 2  # Update to automatically invalidate all previous cookies

# single signon
# set cookie on fablr.co (also works for dev.fablr.co, helmgast.fablr.co, etc
# set cookie on custom domains (helmgast.se, kultdivinitylost.com)
#  method 1 - redirect to them in turn
#  method 2 - embed image requests to a script endpoint
#  method 3 - use AJAX with correct CORS headers on server
# For any of above methods, we need to verify that the request two set the custom domain
# cookies are related to the signon that was just completed, e.g. it needs to be authenticated
# When we visit first custom domain, it wont receive the secure cookie already set on .fablr.co,
# so it needs to be provided in an URL arg. But that URL arg has to be temporary, unguessable and only work
# once, to avoid security holes. CSRF tokens may be one way.
# with this setup there is no subdomain for assets that will not receive cookies


@auth_app.record_once
def on_load(state):
    state.app.before_request(load_user)
    state.app.template_context_processors[None].append(get_context_user)


def populate_user(user, user_info):
    # One time transfer of info from social profile, if any
    if not user.realname:
        user.realname = user_info.get('name', None)
    if not user.username:
        user.username = user_info.get('nickname', None)
    if not user.images:
        picture_url = user_info.get('picture_large', None) or user_info.get('picture', None)
        if picture_url and 'gravatar.com' not in picture_url:
            from fablr.model.asset import FileAsset
            img = FileAsset(owner=user, access_type='hidden', tags=['user'],
                            source_file_url=picture_url)
            try:
                img.save()
                user.images = [img]
            except Exception as e:
                logger.warning(
                    "Unable to load profile image at sign-in for user %s, due to %s" % (user, e))

@auth_app.route('/callback')
def callback():
    support_email = current_app.config['MAIL_DEFAULT_SENDER']
    code = request.args.get('code', None)
    if not code:
        abort(401)

    token_url = "https://{domain}/oauth/token".format(domain=current_app.config['AUTH0_DOMAIN'])

    token_payload = {
        'client_id': current_app.config['AUTH0_CLIENT_ID'],
        'client_secret': current_app.config['AUTH0_CLIENT_SECRET'],
        'redirect_uri': '{server}auth/callback'.format(server=request.host_url),
        'code': code,
        'grant_type': 'authorization_code'
    }
    # Verify the token
    token_info = requests.post(token_url, data=json.dumps(token_payload),
                               headers={'content-type': 'application/json'}).json()
    # Fetch user info
    user_url = "https://{domain}/userinfo?access_token={access_token}" \
        .format(domain=current_app.config['AUTH0_DOMAIN'], access_token=token_info['access_token'])


    user_info = requests.get(user_url).json()
    # print token_info, user_info

    # Make sure next is a relative URL
    next = request.args.get('next', '/')
    if not re_next.match(next):
        next = '/'

    if not user_info or 'email' not in user_info:
        logger.error("Unknown user denied login due to missing from backend {info}".format(info=user_info))
        flash(_('Error logging in, contact %(email)s for support', email=support_email), 'danger')
        return redirect(next)  # RETURN IN ERROR

    if not user_info.get('email_verified', False):
        logger.warning("{user} denied login due to lacking verification".format(user=user))
        flash(_('Check your email inbox for verification link before you can login'), 'warning')
        return redirect(next)  # RETURN IN ERROR

    try:
        user = User.objects(email=user_info['email']).get()
    except User.DoesNotExist:
        # Create new user to sign-in
        user = User(email=user_info['email'])
        logger.info("New user {user} created using {identities}".format(
            user=user_info['email'],
            identities=user_info['identities']))
        populate_user(user, user_info)
        # Send to user profile to check updated profile
        next = url_for('social.UsersView:get', intent='patch', id=user.identifier())
        flash(_('Your new user have been created.'), 'info')

    if user.status == 'deleted':
        flash(_('This user is deleted and cannot be used. Contact %(email)s for support.', email=support_email), 'error')
        logger.error('{user} tried to login but the user is deleted'.format(user=user_info['email']))
        return redirect(next)  # RETURN IN ERROR

    # TODO only while we are migrating
    if user.password or user.google_auth or user.facebook_auth:
        user.password, user.google_auth, user.facebook_aut = None, None, None  # Delete old auth data
        populate_user(user, user_info)
        flash(_('Your user have been migrated to new login system.'), 'info')
        # Send to user profile to check updated profile
        next = url_for('social.UsersView:get', intent='patch', id=user.identifier())

    user.status = 'active'  # We are verified
    user.last_login = datetime.utcnow()
    user.save()
    login_user(user)
    return redirect(next)


@auth_app.route('/logout')
def logout():
    logout_user()
    auth0_url = 'https://{domain}/v2/logout?returnTo={host}'.format(domain=current_app.config['AUTH0_DOMAIN'],
                                                                              host=request.host_url)
    return redirect(auth0_url)


@auth_app.route('/join')
def join():
    # TODO redirect to the Auth0 screen?
    return 404


def get_context_user():
    return {'user': get_logged_in_user()}


def load_user():
    g.user = get_logged_in_user()
    # TODO remove when all users migrated
    if not session.get('v') and not getattr(g, 'user_to_migrate', None):
        # We have an old session, try to fetch a user profile to migrate
        if g.user:
            g.user_to_migrate = g.user
        else:
            u2m = session.get('user_pk', None) or request.args.get('user_to_migrate', None)
            if u2m:
                try:
                    g.user_to_migrate = User.objects(status='active', id=u2m).get()
                except User.DoesNotExist:
                    pass

def check_user(test_fn):
    def decorator(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            user = get_logged_in_user()
            if not user:
                return redirect(url_for('auth.login'))

            if not test_fn(user):
                return redirect(url_for('auth.login'))

            return fn(*args, **kwargs)

        return inner

    return decorator


def login_required(func):
    return check_user(lambda u: True)(func)


def admin_required(func):
    return check_user(lambda u: u.admin)(func)


def login_user(user):
    cart_id = session.get('cid', None)
    session.clear()
    # Puts a version to this cookie so we can invalidate it if needed
    # We could also update SECRET but then we can't read previous cookies.
    # 'v' allows us to read them but still force a new one
    session['v'] = COOKIE_VERSION
    session['ok'] = True  # Consider valid and logged in
    session['uid'] = str(user.id)  # The user ID to associate with
    if cart_id:
        session['cid'] = cart_id  # A cart id from the shop that could come from before we login
    session.permanent = True
    g.user = user
    flash(_('You are logged in as %(user)s with %(email)s', user=user, email=user.email), 'success')


def logout_user():
    # TODO consider clearing the full session to leave no trace
    session.pop('ok', None)
    g.user = None
    flash(u"%s" % _('You are now logged out'), 'success')


def get_logged_in_user():
    # print session

    u = getattr(g, 'user', None)  # See if we already fetched it in this request
    if not u and session.get('ok') and session.get('v') == COOKIE_VERSION:
        try:
            u = User.objects(status='active', id=session.get('uid')).get()
        except User.DoesNotExist:
            logout_user()
            pass

    if "as_user" in request.args and u and u.admin:
        as_user = request.args['as_user']
        if as_user == 'none':
            return None  # Simulate no logged in user
        try:
            u2 = User.objects(username=as_user).get()
            logger.debug("User %s masquerading as %s" % (u, u2))
            return u2
        except User.DoesNotExist:
            pass
    return u


sample_fb = {
    u'age_range': {u'min': 21},
    u'locale': u'en_US',
    u'updated_at': u'2016-08-06T07:08:49.536Z',
    u'installed': True,
    u'third_party_id': u'Ze-ccaYqiUClJwYrIWWg7npIceE',
    u'timezone': 9,
    u'identities': [
        {u'isSocial': True, u'connection': u'facebook', u'user_id': u'507316539704', u'provider': u'facebook'}],
    u'verified': True,
    u'sub': u'facebook|507316539704',
    u'name_format': u'{first} {last}',
    u'given_name': u'Martin',
    u'picture_large': u'https://scontent.xx.fbcdn.net/v/t1.0-1/206372_505788601704_789418523_n.jpg?oh=00df06dbde0066e801dfe1550b91706a&oe=5819BAB5',
    u'is_verified': False,
    u'email': u'ripperdoc@gmail.com',
    u'picture': u'https://scontent.xx.fbcdn.net/v/t1.0-1/c21.21.258.258/s50x50/206372_505788601704_789418523_n.jpg?oh=70f081ae39331dec24cb53f62e62d5d7&oe=581D1AC5',
    u'clientID': u'JAwGB3WgQFDHqQCjRNo0Ij3MPbIEGB1N',
    u'link': u'https://www.facebook.com/app_scoped_user_id/507316539704/',
    u'user_id': u'facebook|507316539704',
    u'nickname': u'ripperdoc',
    u'family_name': u'Fr\xf6jd',
    u'name': u'Martin Fr\xf6jd',
    u'gender': u'male',
    u'created_at': u'2016-08-06T07:08:49.536Z',
    u'cover': {
        u'source': u'https://scontent.xx.fbcdn.net/t31.0-8/s720x720/10954465_508762437114_8713305566062260340_o.jpg',
        u'id': u'508762437114', u'offset_y': 30},
    u'devices': [{u'hardware': u'iPhone', u'os': u'iOS'}, {u'hardware': u'iPad', u'os': u'iOS'}],
    u'updated_time': u'2015-06-05T04:30:45+0000',
    u'context': {u'mutual_likes': {u'data': [], u'summary': {u'total_count': 100}},
                 u'id': u'dXNlcl9jb250ZAXh0OgGQn3A4X7jdQiSuQ99chWM2d1ptN3AXEf4BNs1FlVK8shuSyvfhnkE0OtuBVdNQHiW33cK6VqfZAzRpAhulGRWUlPUphfjTqK23VASbD5YyOT7UZD'},
    u'email_verified': True}

sample_google = {
    u'picture': u'https://lh3.googleusercontent.com/-IUDD5LTox08/AAAAAAAAAAI/AAAAAAAALQg/vxBxQY4cjfs/photo.jpg',
    u'user_id': u'google-oauth2|101739805468412392797',
    u'name': u'Martin Fr\xf6jd',
    u'family_name': u'Fr\xf6jd',
    u'locale': u'en',
    u'email_verified': True,
    u'identities': [
        {u'isSocial': True, u'connection': u'google-oauth2', u'user_id': u'101739805468412392797',
         u'provider': u'google-oauth2'}],
    u'updated_at': u'2016-08-06T07:04:13.779Z',
    u'clientID': u'JAwGB3WgQFDHqQCjRNo0Ij3MPbIEGB1N',
    u'given_name': u'Martin',
    u'gender': u'male',
    u'created_at': u'2016-08-06T07:02:57.270Z',
    u'nickname': u'ripperdoc',
    u'email': u'ripperdoc@gmail.com',
    u'sub': u'google-oauth2|101739805468412392797'}