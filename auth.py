"""
    raconteur.auth
    ~~~~~~~~~~~~~~~~

   Authentication module that provides login and logout features on top of
   User model. Adapted from flask-peewee.

    :copyright: (c) 2014 by Raconteur
"""

import functools
import os
import random

from flask import Blueprint, render_template, abort, request, session, flash
from flask import redirect, url_for, g, make_response
from flask_wtf import Form
from wtforms import TextField, PasswordField, validators
from hashlib import sha1, md5
from flask.ext.babel import gettext as _
from flask.ext.mongoengine.wtf import model_form

from oauth2client.client import AccessTokenRefreshError, OAuth2WebServerFlow, FlowExchangeError

current_dir = os.path.dirname(__file__)

# borrowing these methods, slightly modified, from django.contrib.auth
def get_hexdigest(salt, raw_password):
  return sha1(salt + raw_password).hexdigest()

def make_password(raw_password):
  salt = get_hexdigest(str(random.random()), str(random.random()))[:5]
  hsh = get_hexdigest(salt, raw_password)
  return '%s$%s' % (salt, hsh)

def check_password(raw_password, enc_password):
  salt, hsh = enc_password.split('$', 1)
  return hsh == get_hexdigest(salt, raw_password)

def get_next():
  if not request.query_string:
    return request.path
  return '%s?%s' % (request.path, request.query_string)

def create_token(input_string):
  return md5(input_string.strip().lower().encode('utf-8') + u'e3af71457ddb83c51c43c7cdf6d6ddb3').hexdigest()


class LoginForm(Form):
  username = TextField(_('Username'), validators=[validators.Required()])
  password = PasswordField(_('Password'), validators=[validators.Required()])

class TokenForm(Form):
  email = TextField(_('Email'), validators=[validators.Required()])
  token = TextField(_('Token'), validators=[validators.Required()])

class BaseUser(object):
    def set_password(self, password):
      self.password = make_password(password)

    def check_password(self, password):
      return check_password(password, self.password)


class Auth(object):
  def __init__(self, app, db, user_model=None, prefix='/auth', name='auth',
       clear_session=False):
    self.app = app
    self.db = db

    self.User = user_model or self.get_user_model()
    self.JoinForm = model_form(self.User, only=['username', 'password', 'email',
      'realname', 'location', 'description'], field_args={'password':{'password':True}})
    self.JoinForm.confirm_password = PasswordField(_('Confirm Password'), 
        validators=[validators.Required(), validators.EqualTo('password', message=_('Passwords must match'))])
    self.blueprint = self.get_blueprint(name)
    self.url_prefix = prefix
    self.google_client = [app.config['GOOGLE_CLIENT_ID'], app.config['GOOGLE_CLIENT_SECRET'], '']
    self.clear_session = clear_session

    self.setup()

  def get_context_user(self):
    return {'user': self.get_logged_in_user()}

  def get_user_model(self):
    class User(self.db.Model, BaseUser):
      username = CharField(unique=True)
      password = CharField()
      email = CharField(unique=True)
      active = BooleanField()
      admin = BooleanField(default=False)

      def __unicode__(self):
        return self.username
    return User

  def get_blueprint(self, blueprint_name):
    return Blueprint(
      blueprint_name,
      __name__,
      static_folder=os.path.join(current_dir, 'static'),
      template_folder=os.path.join(current_dir, 'templates'),
    )

  def get_urls(self):
    return (
      ('/logout/', self.logout),
      ('/login/', self.login),
      ('/verify/', self.verify),
      ('/join/', self.join),
    )

  def get_login_form(self):
    return LoginForm

  def test_user(self, test_fn):
    def decorator(fn):
      @functools.wraps(fn)
      def inner(*args, **kwargs):
        user = self.get_logged_in_user()
        if not user:
          return redirect(url_for('%s.login' % self.blueprint.name, next=get_next()))

        if not test_fn(user):
          return redirect(url_for('%s.login' % self.blueprint.name, next=get_next()))

        return fn(*args, **kwargs)
      return inner
    return decorator

  def login_required(self, func):
    return self.test_user(lambda u: True)(func)
  
  def admin_required(self, func):
    return self.test_user(lambda u: u.admin)(func)

  def login_user(self, user):
    session['logged_in'] = True
    session['user_pk'] = str(user.id)
    session.permanent = True
    g.user = user
    flash( _('You are logged in as') + ' %s' % user.username, 'success')

  def logout_user(self, user):
    if self.clear_session:
      session.clear()
    else:
      session.pop('logged_in', None)
    g.user = None
    flash( _('You are now logged out'), 'success')

  def get_logged_in_user(self):
    if session.get('logged_in'):
      if getattr(g, 'user', None):
        return g.user
      try:
        return self.User.objects(
          status='active', id=session.get('user_pk')
        ).get()
      except self.User.DoesNotExist:
        session.pop('logged_in', None)
        pass

  def join(self):
    # if request has google code
      # run google process to get auth token
      # if success, add user google data to user profile, and login immediately
    # else check form as below

    if g.feature and not g.feature['join']:
      raise ResourceError(403)
    form = self.JoinForm()
    if request.method == 'POST' and request.form['username']:
      # Read username from the form that was posted in the POST request
      form.process(request.form)
      if form.validate():
        try:
          self.User.objects().get(username=form.username.data)
          flash(_('That username is already taken'), 'warning')
        except self.User.DoesNotExist:
          user = self.User(status='invited')
          form.populate_obj(user)
          user.save()
          self.login_user(user)
          return redirect(url_for('homepage'))
      flash(_('Error in form' ), 'warning')
    return render_template('auth/auth_form.html', form=form, op='join')

  def verify(self):
    # if request has google code
      # run google process to get auth token
      # if success, add user google data to user profile, and login immediately
    # else check form as below

    email = request.args.get('email')
    token = request.args.get('token')
    if request.method == 'POST':
      pass
    if email and token:
      user = self.User.objects(email=email).first()
      if user and create_token(user.email) == token:
        if user.status != 'invited':
          flash( _('You have already verified this account'), 'warning')
          return redirect(url_for('homepage'))
          # Return error, already active!
        elif len(user.password)>40: # 40+ char hash
          # User has given password before, we are just doing the email verification
          # For max security, we should check password here again
          user.status = 'active'
          user.save()
          # Verify account
          self.login_user(user)
          flash( "%s %s %s" % (_('Username'), user.username,_('is now verified!')), 'success')
          return redirect(request.args.get('next') or url_for('homepage'))
        else: # email is verified, but account registration hasn't completed
          form = self.JoinForm(obj=user)
          return render_template('auth/auth_form.html', form=form, op='verify')
    flash( _('Incorrect verification link'), 'danger')
    return redirect(url_for('homepage'))

  def connect_google(self, one_time_code):
    try:
      # Upgrade the authorization code into a credentials object
      # oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
      oauth_flow = OAuth2WebServerFlow(*self.google_client)
      oauth_flow.redirect_uri = 'postmessage'
      credentials = oauth_flow.step2_exchange(one_time_code)
    except FlowExchangeError:
      raise Forbidden('Failed to upgrade the authorization code.') # 401
    gplus_id = credentials.id_token['sub']
    
    stored_credentials = session.get('gplus_token')
    stored_gplus_id = session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
      return 'Current user is already connected.', 200
    # Store the access token in the session for later use.
    session['gplus_token'] = credentials.access_token
    session['gplus_id'] = gplus_id
    return 'Successfully connected user.', 200

  def login(self):
    # if request has google code
      # run google process to get auth token
      # if success, process successful login as below
    # else check form as below

    Form = self.get_login_form()
    if request.method == 'POST':
      if request.args.has_key('connect_google'):
        self.connect_google(request.data)
        user = self.User.objects(external_service='google', external_id=session['gplus_id']).get()            
        # TBD
      else:
        form = Form(request.form)
        if form.validate():
          try:
            user = self.User.objects(username=form.username.data).get()
            if user.status == 'active' and user.check_password(form.password.data):
              self.login_user(user)
              return redirect(request.args.get('next') or url_for('homepage'))
          except self.User.DoesNotExist:
            pass # will get to error state below
          flash( _('Incorrect username or password (or you need to verify the \
            account - check your email)'), 'danger')
    else:
      form = Form()
    return render_template('auth/auth_form.html', form=form, op='login')

  def logout(self):
    # if user is logged in via google, send token revoke
    self.logout_user(self.get_logged_in_user())
    return redirect(request.args.get('next') or url_for('homepage'))

  def configure_routes(self):
    for url, callback in self.get_urls():
      self.blueprint.route(url, methods=['GET', 'POST'])(callback)

  def register_blueprint(self, **kwargs):
    self.app.register_blueprint(self.blueprint, url_prefix=self.url_prefix, **kwargs)

  def load_user(self):
    g.user = self.get_logged_in_user()

  def register_handlers(self):
    self.app.before_request(self.load_user)

  def register_context_processors(self):
    self.app.template_context_processors[None].append(self.get_context_user)

  def setup(self):
    self.configure_routes()
    self.register_blueprint()
    self.register_handlers()
    self.register_context_processors()