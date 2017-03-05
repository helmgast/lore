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

import facebook
import httplib2
import requests

from flask import Blueprint, request, session, flash
from flask import abort
from flask import current_app
from flask import logging
from flask import redirect, url_for, g
from flask import render_template
from flask.ext.mongoengine.wtf import model_form
from flask_babel import lazy_gettext as _
from googleapiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow
from wtforms import HiddenField

from fablr.controller.resource import re_next, RacModelConverter
from fablr.model.baseuser import check_password
from fablr.model.user import User

logger = current_app.logger if current_app else logging.getLogger(__name__)

auth_app = Blueprint('auth', __name__, template_folder='../templates/auth')

COOKIE_VERSION = 1  # Update to automatically invalidate all previous cookies

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
    state.app.login_required = login_required
    state.app.admin_required = admin_required


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
                    u"Unable to load profile image at sign-in for user %s, due to %s" % (user, e))

def get_next_url():
    rv = request.args.get('next', '/')
    if not re_next.match(rv):
        rv = '/'
    return rv

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
    next_url = get_next_url()

    if not user_info or 'email' not in user_info:
        logger.error("Unknown user denied login due to missing from backend {info}".format(info=user_info))
        flash(_('Error logging in, contact %(email)s for support', email=support_email), 'danger')
        return redirect(next)  # RETURN IN ERROR

    if not user_info.get('email_verified', False):
        logger.warning("{user} denied login due to lacking verification".format(user=user_info))
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
        next_url = url_for('social.UsersView:get', intent='patch', id=user.identifier())
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
        next_url = url_for('social.UsersView:get', intent='patch', id=user.identifier())

    user.status = 'active'  # We are verified
    user.last_login = datetime.utcnow()
    user.save()
    login_user(user)
    return redirect(next_url)


@auth_app.route('/logout')
def logout():
    logout_user()
    auth0_url = 'https://{domain}/v2/logout?returnTo={host}'.format(domain=current_app.config['AUTH0_DOMAIN'],
                                                                              host=request.host_url)
    return redirect(auth0_url)


@auth_app.route('/login')
def login():
    # TODO redirect to the Auth0 screen?
    abort(404)


@auth_app.route('/join')
def join():
    # TODO redirect to the Auth0 screen?
    abort(404)


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
    return u  # Might be None if all failed above


# ---------- Old auth, for migration purposes only ----------- #

google_client = None
google_api = None
facebook_client = None

if 'GOOGLE_CLIENT_ID' in current_app.config and 'GOOGLE_CLIENT_SECRET' in current_app.config:
    google_client = [current_app.config['GOOGLE_CLIENT_ID'], current_app.config['GOOGLE_CLIENT_SECRET'], '']
    google_api = build('plus', 'v1')
if 'FACEBOOK_APP_ID' in current_app.config and 'FACEBOOK_APP_SECRET' in current_app.config:
    facebook_client = {'app_id': current_app.config['FACEBOOK_APP_ID'],
                            'app_secret': current_app.config['FACEBOOK_APP_SECRET']}

LoginForm = model_form(User, only=['email', 'password'], field_args={'password': {'password': True}},
                        converter=RacModelConverter())
LoginForm.auth_code = HiddenField(_('Auth Code'))
LoginForm.external_service = HiddenField(_('External Service'))

RemindForm = model_form(User, only=['email'])


def connect_google(one_time_code):
    if not google_client:
        raise Exception('No Google client configured')

    # Upgrade the authorization code into a credentials object
    # oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
    oauth_flow = OAuth2WebServerFlow(*google_client)
    oauth_flow.redirect_uri = 'postmessage'
    credentials = oauth_flow.step2_exchange(one_time_code)
    http = httplib2.Http()
    http = credentials.authorize(http)
    google_request = google_api.people().get(userId='me')
    profile = google_request.execute(http=http)
    return credentials, profile


def connect_facebook(short_access_token):
    if not facebook_client:
        raise Exception('No Facebook client configured')
    graph = facebook.GraphAPI(short_access_token)
    resp1 = graph.extend_access_token(facebook_client['app_id'], facebook_client['app_secret'])
    resp2 = graph.get_object('me')
    return resp1['access_token'], resp2['id'], resp2['email']


@auth_app.route('/migrate')
def migrate():
    form = LoginForm()
    if request.method == 'POST':
        form.process(request.form)
        if form.auth_code.data and form.external_service.data:
            # We have been authorized through external service
            if form.external_service.data in ['google', 'facebook']:
                try:
                    if form.external_service.data == 'google':
                        credentials, profile = connect_google(form.auth_code.data)
                        provided_external_id = credentials.id_token['sub']
                        external_access_token = credentials.access_token
                        # Update the token, as it may have expired and been renewed
                        user = User.objects(google_auth__id=provided_external_id).get()
                        user.google_auth.long_token = external_access_token
                    elif form.external_service.data == 'facebook':
                        external_access_token, provided_external_id, email = connect_facebook(
                            form.auth_code.data)
                        user = User.objects(facebook_auth__id=provided_external_id).get()
                        # Update the token, as it may have expired and been renewed
                        user.facebook_auth.long_token = external_access_token
                    if user.status == 'active':
                        user.last_login = datetime.utcnow()
                        user.save()
                        login_user(user)
                        # ---- SUCCESS --- #
                        return redirect(get_next_url())
                    else:
                        flash(_('This user account is not active or verified'), 'danger')
                except User.DoesNotExist:
                    flash(_('No matching external authentication, are you sure you signed up with this method?'),
                          'danger')
                except Exception as e:
                    logger.exception('Error contacting external service')
                    flash(u"%s %s" % (_('Error contacting external service'), e), 'danger')
            else:
                flash(_('Incorrect external service supplied'), 'danger')

        elif form.validate():
            # External service not used, let's check password
            try:
                user = User.objects(email=form.email.data.lower()).get()
                if user.status == 'active' and check_password(form.password.data, user.password):
                    user.last_login = datetime.utcnow()
                    user.save()
                    login_user(user)
                    # ---- SUCCESS --- #
                    return redirect(get_next_url())
                else:
                    flash(_('Incorrect username or password'), 'danger')
            except User.DoesNotExist:
                flash(_('No such user exist, are you sure you registered first?'), 'danger')
        else:
            logger.error(form.errors)
            flash(_('Error in form'), 'danger')
    return render_template('auth/migrate.html', form=form, op='login')


@auth_app.route('/remind')
def remind():
    # TODO Don't like importing this here but can't find another way to
    # avoid import errors
    from mailer import send_mail

    form = RemindForm()
    if request.method == 'POST':
        form.process(request.form)
        if form.validate():
            try:
                user = User.objects(email=form.email.data.lower()).get()
                send_mail(
                    [user.email],
                    _('Reminder on how to login to Helmgast.se'),
                    mail_type='remind_login',
                    user=user
                )
                flash(_('Reminder email sent to your address'), 'success')
            except User.DoesNotExist:
                flash(_('No such user exist, are you sure you registered first?'), 'danger')
        else:
            flash(_('Errors in form'), 'danger')
    return render_template('auth/remind.html', form=form)