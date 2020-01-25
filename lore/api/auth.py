"""
    lore.auth
    ~~~~~~~~~~~~~~~~

   Authentication module that provides login and logout features on top of
   User model, uses Auth0.com as authentication backend.

    :copyright: (c) 2016 by Helmgast AB
"""

from builtins import str
import functools
import json
from datetime import datetime

import requests
from flask import Blueprint, request, session, flash
from flask import abort
from flask import current_app
from flask import logging
from flask import redirect, url_for, g
from flask import render_template
from flask_babel import lazy_gettext as _
from mongoengine import MultipleObjectsReturned, DoesNotExist, Q
from werkzeug.urls import url_encode, url_quote
from sentry_sdk import configure_scope, capture_message, capture_exception

from lore.model.misc import safe_next_url, set_lang_options
from lore.model.user import User, UserStatus
from lore.model.world import Publisher
from auth0.v3.management import Auth0
from auth0.v3.authentication import GetToken

logger = current_app.logger if current_app else logging.getLogger(__name__)

auth_app = Blueprint('auth', __name__)
auth0_domain = ''
auth0_mgmt_client = None
auth0_mgmt_token = {}
auth0_mgmt_token_expiry = None
token_getter = None

# single signon
# set cookie on lore.pub (also works for subdomains like helmgast.lore.pub, etc
# set cookie on custom domains (helmgast.se, kultdivinitylost.com)
#  method 1 - redirect to them in turn
#  method 2 - embed image requests to a script endpoint
#  method 3 - use AJAX with correct CORS headers on server
# For any of above methods, we need to verify that the request two set the custom domain
# cookies are related to the signon that was just completed, e.g. it needs to be authenticated
# When we visit first custom domain, it wont receive the secure cookie already set on .lore.pub,
# so it needs to be provided in an URL arg. But that URL arg has to be temporary, unguessable and only work
# once, to avoid security holes. CSRF tokens may be one way.
# with this setup there is no subdomain for assets that will not receive cookies

# https://helmgast.eu.auth0.com/authorize?client_id=JAwGB3WgQFDHqQCjRNo0Ij3MPbIEGB1N&response_type=code&redirect_uri=http://*.lore.pub/auth/callback
# https://helmgast.eu.auth0.com/login?client=JAwGB3WgQFDHqQCjRNo0Ij3MPbIEGB1N

# Attach hooks at blueprint init time, instead of at import time
@auth_app.record_once
def on_load(state):
    global auth0_domain, auth0_client_id, auth0_client_secret, token_getter
    state.app.before_request(load_user)
    state.app.template_context_processors[None].append(get_context_user)
    state.app.login_required = login_required
    state.app.admin_required = admin_required
    auth0_domain = current_app.config['AUTH0_DOMAIN']
    auth0_client_id = current_app.config['AUTH0_CLIENT_ID']
    auth0_client_secret = current_app.config['AUTH0_CLIENT_SECRET']
    token_getter = GetToken(auth0_domain)

def get_mgmt_api():
    global auth0_mgmt_token, auth0_mgmt_token_expiry, auth0_mgmt_client
    if not auth0_mgmt_token or datetime.utcnow().timestamp() > auth0_mgmt_token_expiry:
        auth0_mgmt_token = token_getter.client_credentials(auth0_client_id, auth0_client_secret, 'https://{}/api/v2/'.format(auth0_domain))
        logger.info(auth0_mgmt_token)
        auth0_mgmt_token_expiry = datetime.utcnow().timestamp() + auth0_mgmt_token['expires_in']
        auth0_mgmt_client = Auth0(auth0_domain, auth0_mgmt_token['access_token'])
    return auth0_mgmt_client

def populate_user(user, user_info, token_info=None):
    if not user.realname:
        user.realname = user_info.get('name', None)
    if not user.username:
        user.username = user_info.get('nickname', None)
    if not user.avatar_url:
        user.avatar_url = user_info.get('picture', None)
    user.identities = user_info['identities']
    if token_info:
        user.access_token = token_info['access_token']
    return user

@auth_app.route('/callback', subdomain='<pub_host>')
def callback():
    # Note: This callback applies both to login and signup, there is no difference.

    support_email = current_app.config['MAIL_DEFAULT_SENDER']
    code = request.args.get('code', None)
    if not code:
        # It probably a token callback, using the # fragments on URL. We can't see from server
        abort(400)

    token_url = "https://{domain}/oauth/token".format(domain=auth0_domain)

    token_payload = {
        'client_id': auth0_client_id,
        'client_secret': auth0_client_secret,
        'redirect_uri': url_for('auth.callback', pub_host=g.pub_host, _external=True, _scheme=request.scheme),
        'code': code,
        'grant_type': 'authorization_code'
    }
    # Verify the token
    token_info = requests.post(token_url, data=json.dumps(token_payload),
                               headers={'content-type': 'application/json'}).json()

    # Fetch user info
    user_url = "https://{domain}/userinfo?access_token={access_token}" \
        .format(domain=auth0_domain, access_token=token_info['access_token'])

    user_info = requests.get(user_url).json()

    # Make sure next is a relative URL
    next_url = safe_next_url(default_url='/')

    if not user_info:
        msg = f"Unknown user denied login due to missing info from backend {user_info}"
        logger.error(msg)
        logout_user()
        flash(_('Error logging in, contact %(email)s for support', email=support_email), 'danger')
        capture_message(msg)
        return redirect(next_url)  # RETURN IN ERROR

    if not user_info.get('email_verified', False):
        msg = f"{user_info} denied login due to lacking verification"
        logger.warning(msg)
        logout_user()
        flash(_('Check your email inbox for verification link before you can login'), 'warning')
        capture_message(msg)
        return redirect(next_url)  # RETURN IN ERROR

    # Authenticating user exists in DB
        # Another user logged in (session user)
        # Another session not logged in
    # Authenticating user doesn't exist in DB
        # Another user logged in (session user)
        # Another session not logged in
    # Attempting link?


    email = user_info['email']
    session_user = get_logged_in_user(require_active=False)
    auth_user = None

    # Find user that matches the provided auth email
    # Will look in identities, but if Auth0 works correctly, we shouldn't arrive here with an email that is not primary (e.g. not in identities)
    try:
        auth_user = User.query_user_by_email(email).get()
        if auth_user.status == 'deleted':
            flash(_('This user is deleted and cannot be used. Contact %(email)s for support.', email=support_email),
                  'error')
            msg = u'{user} tried to login but the user is deleted'.format(user=email)
            capture_message(msg)
            logger.error(msg)
            return redirect(next_url)  # RETURN IN ERROR
    except DoesNotExist:
        pass

    if 'link' in request.args and request.args['link']:
        # We are requested to link accounts
        if session_user and session_user.email == request.args['link']:  # The logged in user is the primary from link arg
            if session_user != auth_user and session_user.email != user_info['email']:  # Authenticating user is empty or different from logged in user
                primary_id = f"{session_user.identities[0]['provider']}|{session_user.identities[0]['user_id']}"
                identities = get_mgmt_api().users.link_user_account(primary_id, {
                    "user_id": user_info['identities'][0]['user_id'],
                    "provider": user_info['identities'][0]['provider']
                })
                # As we linked auth_user to session_user, we can keep current session
                session_user.identities = identities
                populate_user(session_user, user_info)
                session_user.save()
                flash(_("You linked email %(email)s to primary %(primary)s", email=user_info['email'], primary=session_user.email), 'info')
            # If not, we essentially do nothing, as the user is already itself
            return redirect(next_url)
        else:  # Something went wrong, there is no valid logged in user
            msg = f"Invalid linking attempt session_user {session_user}, link arg {request.args['link']}"
            logger.error(msg)
            capture_message(msg)
            abort(400)

    if not auth_user:
        # We have neither user from session or from login. Create a new user!
        user = User(email=email)
        user.save()  # So that we are guaranteed to have a user id for add_auth()
        logger.info(u"New user {user} created using {identities}".format(
            user=user_info['email'],
            identities=user_info['identities']))
        flash(_('Your new user have been created.'), 'info')
    else:
        user = auth_user

    populate_user(user, user_info, token_info)
    if user.status == 'invited':
        # Keep sending to user profile if we are still invited
        next_url = url_for('social.UsersView:get', intent='patch', id=user.identifier(), next=next_url)
        flash(_('Save your profile before you can use your new user!'), 'info')
    else:
        flash(_('You are logged in as %(user)s with %(email)s', user=user, email=user_info['email']), 'success')

    user.last_login = datetime.utcnow()
    user.logged_in = True
    user.save()

    login_user(user)
    return redirect(next_url)


@auth_app.route('/sso', subdomain='<pub_host>')
def sso():
    url = auth0_url(action='login')
    return redirect(url)


@auth_app.route('/logout', subdomain='<pub_host>')
def logout():
    # Clears logged in flag to effectively log out from all domains, even if session is only cleared in current domain.
    publisher = Publisher.objects(slug=g.pub_host).first()
    set_lang_options(publisher)

    logout_user()
    flash(_('You are now logged out'), 'success')
    url = auth0_url(action='logout')

    return redirect(url)


@auth_app.route('/login', subdomain='<pub_host>')
def login():
    publisher = Publisher.objects(slug=g.pub_host).first()
    set_lang_options(publisher)
    return render_template('auth/login.html')


@auth_app.route('/join')
def join():
    # TODO redirect to the Auth0 screen?
    abort(404)


def auth0_url(action='login', callback_args=None, **kwargs):
    if not callback_args:
        callback_args = {}
    domain = current_app.config['AUTH0_DOMAIN']
    client_id = current_app.config['AUTH0_CLIENT_ID']
    # prompt=login
    # prompt=none
    if action=='login':
        if 'next' not in callback_args:
            callback_args['next'] = safe_next_url()
        callback_url = url_for('auth.callback', pub_host=g.pub_host, _external=True, _scheme=request.scheme, **callback_args)
        url = f'https://{domain}/authorize?client_id={client_id}&response_type=code&redirect_uri={url_quote(callback_url, safe="")}'
    elif action=='logout':
        home = url_for('world.ArticlesView:publisher_home', _external=True, _scheme=request.scheme)
        url = f'https://{domain}/v2/logout?returnTo={home}'
    if kwargs:
        url = url + '&' + url_encode(kwargs)
    return url

def get_context_user():
    return {'user': get_logged_in_user()}


def load_user():
    g.user = get_logged_in_user()
    if g.user:
        with configure_scope() as scope:
            scope.user = {"email": g.user.email, "id": g.user.id}


# TODO update or depcrecate
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
    # cart_id = session.get('cid', None)
    session['uid'] = str(user.id)  # The user ID to save for longer
    # if cart_id:
    #     session['cid'] = cart_id  # A cart id from the shop that could come from before we login
    session.permanent = True  # Default 30 days
    g.user = user


def logout_user():
    session.clear()
    if getattr(g, 'user', None):
        g.user.logged_in = False
        g.user.save()
        g.user = None


def get_logged_in_user(require_active=True):
    u = getattr(g, 'user', None)  # See if we already fetched it in this request
    if not u:
        uid = session.get('uid', None)
        if uid:
            try:
                # Temporarily allow us to decode bytes from cookies, as we transition from cookies written from
                # py2.7 (bytes) to py 3.6 (unicode)
                if hasattr(uid, 'decode'):
                    uid = uid.decode()
                u = User.objects(id=uid).first()
                if u:
                    if not u.logged_in or (require_active and u.status != UserStatus.active):
                        logger.warning(f"User {u} forced out: logged_in={u.logged_in}, status={u.status}, "
                                       f"require_active={require_active}, url {request.url}")
                        capture_message
                        # We are logged out or user has become other than active
                        return None

                    if "as_user" in request.args and u and u.admin:
                        as_user = request.args['as_user']
                        if as_user == 'none':
                            return None  # Simulate no logged in user
                        u2 = User.query_user_by_email(email=as_user).first()
                        if u2:
                            logger.debug("User %s masquerading as %s" % (u, u2))
                            return u2
                else:
                    logger.warning("No user in database with uid {uid}".format(uid=uid))
            except Exception as e:
                logger.error(e)
                capture_exception(e)
                logout_user()
    return u  # Might be None if all failed above
