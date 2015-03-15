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
from wtforms import TextField, PasswordField, HiddenField, validators
from wtforms.widgets import HiddenInput
from flask.ext.babel import lazy_gettext as _
from flask.ext.mongoengine.wtf import model_form
from mongoengine import ValidationError

import httplib2
import requests
from oauth2client.client import AccessTokenRefreshError, OAuth2WebServerFlow, FlowExchangeError
from apiclient.discovery import build
import facebook

from baseuser import BaseUser, check_password

current_dir = os.path.dirname(__file__)

def get_next():
  if not request.query_string:
    return request.path
  return '%s?%s' % (request.path, request.query_string)

class Auth(object):
  def __init__(self, app, db, user_model=None, ext_auth_model=None, prefix='/auth', name='auth',
       clear_session=False):
    self.app = app
    self.db = db

    self.User = user_model or self.get_user_model()
    if not ext_auth_model:
      raise ValueError("Current version cannot work without access to ExternalAuth")
    self.ExternalAuth = ext_auth_model
    self.blueprint = self.get_blueprint(name)
    self.url_prefix = prefix
    if 'GOOGLE_CLIENT_ID' in app.config and 'GOOGLE_CLIENT_SECRET' in app.config:
      self.google_client = [app.config['GOOGLE_CLIENT_ID'], app.config['GOOGLE_CLIENT_SECRET'], '']
    if 'FACEBOOK_APP_ID' in app.config and 'FACEBOOK_APP_SECRET' in app.config:
      self.facebook_client = {'app_id': app.config['FACEBOOK_APP_ID'], 'app_secret':app.config['FACEBOOK_APP_SECRET']}
    self.clear_session = clear_session
    self.logger = app.logger
    app.login_required = self.login_required
    app.admin_required = self.admin_required
    app.access_policy = {} # Set up dict for access policies to be stored in

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
      ('/join/', self.join),
      ('/remind/', self.remind)     
    )

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
    flash( u"%s %s" % (_('You are logged in as'), user), 'success')

  def logout_user(self, user):
    if self.clear_session:
      session.clear()
    else:
      session.pop('logged_in', None)
    g.user = None
    flash( u"%s" % _('You are now logged out'), 'success')

  def get_logged_in_user(self):
    # if request.endpoint and request.endpoint[0:4]=='auth':
    #   print session
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

  def connect_google(self, one_time_code):
    if not self.google_client:
      raise Exception('No Google client configured')
    # Upgrade the authorization code into a credentials object
    # oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
    oauth_flow = OAuth2WebServerFlow(*self.google_client)
    oauth_flow.redirect_uri = 'postmessage'
    credentials = oauth_flow.step2_exchange(one_time_code)
    http = httplib2.Http()
    http = credentials.authorize(http)
    google_request = GOOGLE.people().get(userId='me')
    profile = google_request.execute(http=http)
    return credentials, profile

  def connect_facebook(self, short_access_token):
    if not self.facebook_client:
      raise Exception('No Facebook client configured')
    graph = facebook.GraphAPI(short_access_token)
    resp1 = graph.extend_access_token(self.facebook_client['app_id'], self.facebook_client['app_secret'])
    resp2 = graph.get_object('me')
    return resp1['access_token'], resp2['id'], resp2['email']

  def get_next_url(self):
    n = request.args.get('next', None)
    # Avoid going next to other auth-pages, will just be confusing!
    return n if (n and '/auth/' not in n) else url_for('homepage')

  def join(self):
    # This function does joining in several steps.
    # Join-step: no user (should) exist
    # Verify-step: a user exists, and we are amending details
    # bb@bb.com, 9db26ad4ea2469e547f45b873c19ff99

    print request.form
    # if g.feature and not g.feature['join']:
    #   raise ResourceError(403)

    form = self.JoinForm()
    op = 'join'
    if request.method == 'GET':
      if request.args.has_key('email') and request.args.has_key('email_token'):
        op = 'verify'
        form.process(request.args) # add email and email_token to the form
    if request.method == 'POST':
      form.process(request.form)

      # Need to deal with email and password specifically here.
      # If we are coming from here with external auth or email token, we shouldn't
      # change any existing password, so remove from form
      if (form.auth_code.data and form.external_service.data):
        # User is either using external auth or verifying an email, no need for
        # password so remove to make sure nothing can be changed
        del form.password
        del form.confirm_password
      if form.validate():
        if form.auth_code.data:
          if form.external_service.data in ['google','facebook']:
            # User is trying to create data from external auth (can come here both
            # with an email_token as well or without)
            try:
              user = self.User.objects(email=form.email.data.lower()).get()
            except self.User.DoesNotExist:            
              user = self.User()
            # We could get here if someone puts in another person's email
            if not (user.status != 'invited' or user.facebook_auth or user.google_auth or user.password):
              if form.external_service.data == 'google':
                credentials, profile = self.connect_google(form.auth_code.data)
                external_id, external_access_token = credentials.id_token['sub'], credentials.access_token
                emails = [line['value'] for line in profile['emails']]
                # print "Google email", emails, profile['emails']
                if not (external_id or external_access_token):
                  raise ValueError('Error connecting to Google')
                user.google_auth = self.ExternalAuth(
                  id=external_id,
                  long_token=external_access_token, 
                  emails=emails)
              elif form.external_service.data == 'facebook':
                external_access_token, external_id, email = self.connect_facebook(form.auth_code.data)
                emails = [email]
                # print "Facebook email", emails
                if not (external_id or external_access_token):
                  raise ValueError('Error connecting to Facebook')
                user.facebook_auth = self.ExternalAuth(
                  id=external_id,
                  long_token=external_access_token, 
                  emails=emails)
              form.populate_obj(user) # Will not save any data on external service!

              if form.email.data in emails or (create_token(form.email.data) == form.email_token.data):
                # This user has a verified email
                user.status = 'active'
                user.save()
                self.login_user(user)
                return redirect(self.get_next_url())               
              else:
                user.save()
                #send_verification_email()
                print "Sending verification email" #TODO
                flash( _('There is a problem with your login, please contact us info@helmgast.se!'), 'warning')
                
                # flash( _("You have registered, but as your preferred email didn't \
                #   match the ones in external auth, you have to verify it manually, \
                #   please check your inbox"), 'success')
            else:
              # print user.status, user.facebook_auth, user.google_auth, user.password
              # we can't create on a user which has already been create in some way or another
              flash( _('Someone has already created this user!'), 'warning')
          else:
           flash( _('Form data has been manipulated, unsupported external auth service'), 'warning')

        elif form.email_token.data:
          # User is not using external auth but came here with email token, so
          # account already exists
          if (create_token(form.email.data) == form.email_token.data):
            # Email has been verified, so we set to active and populate the user
            try:
              user = self.User.objects(email=form.email.data.lower()).get()
              if user.status == 'invited':
                user.status = 'active'
                form.populate_obj(user) # any optional data that has been added
                user.save()
                self.login_user(user)
                return redirect(self.get_next_url())                
              else:
                flash( _('This user is already verified!'), 'warning')
            except:
              flash( _('No invitation for this email and token exists'), 'warning')
          else:
            # Something wrong with the token
            flash( _('Incorrect email or email token, did you use the right link?'), 'danger')
        
        else:
          flash( _('Registration without invite link is not yet open, please come back later!'), 'danger')

          # User is submitting a "vanilla" user registration without external auth
          # try:
          #   user = self.User.objects(email=form.email.data).get()
          #   # we shouldn't get here if no user existed, so it means we are joining
          #   # with an existing email!
          #   flash( _('A user with this email already exists'), 'warning')
          # except self.User.DoesNotExist:
          #   # No user above was found with the provided email
          #   user = self.User()
          #   form.populate_obj(user)
          #   user.save()
          #   #send_verification_email()
          #   print "Sending verification email" #TODO
          #   flash( u'%s %s (%s)' % (_('A verification email have been sent out to'), form.email.data, create_token(form.email.data)), 'success')
      else:
        flash( u"%s: %s" % (_('Error in form'), form.errors), 'warning')

    return render_template('auth/join.html', form=form, op=op)

  def login(self):
    print request.form
    form = self.LoginForm()
    if request.method == 'POST':
      form.process(request.form)
      if form.auth_code.data and form.external_service.data:
        # We have been authorized through external service
        if form.external_service.data in ['google','facebook']:
          try:
            if form.external_service.data=='google':
              credentials, profile = self.connect_google(form.auth_code.data)
              provided_external_id = credentials.id_token['sub']
              external_access_token = credentials.access_token  
              # Update the token, as it may have expired and been renewed
              user = self.User.objects(google_auth__id=provided_external_id).get()
              user.google_auth.long_token = external_access_token
            elif form.external_service.data=='facebook':
              external_access_token, provided_external_id, email = self.connect_facebook(form.auth_code.data)
              user = self.User.objects(facebook_auth__id=provided_external_id).get()
              # Update the token, as it may have expired and been renewed
              user.facebook_auth.long_token = external_access_token
            if user.status == 'active':
              user.save()
              self.login_user(user)
              return redirect(self.get_next_url())
            else:
              flash( _('This user account is not active or verified'), 'danger')
          except self.User.DoesNotExist:
            flash( _('No matching external authentication, are you sure you signed up with this method?'), 'danger')          
          except Exception as e:
            flash( u"%s %s" % (_('Error contacting external service'),e), 'danger')
        else:
          flash( _('Incorrect external service supplied'), 'danger')
        
      elif form.validate():
        try:
          user = self.User.objects(email=form.email.data.lower()).get()
          if user.status=='active' and check_password(form.password.data, user.password):
            self.login_user(user)
            return redirect(self.get_next_url())
          else:
            flash( _('Incorrect username or password'), 'danger')
        except self.User.DoesNotExist:
          flash( _('No such user exist, are you sure you registered first?'), 'danger')
      else:
        flash( _('Errors in form'), 'danger')
    return render_template('auth/login.html', form=form, op='login')

  def logout(self):
    # if user is logged in via google, send token revoke
    self.logout_user(self.get_logged_in_user())
    return redirect(self.get_next_url())

  def remind(self):
    # TODO Don't like importing this here but can't find another way to
    # avoid import errors
    from controller.mailer import send_mail

    form = self.RemindForm()
    if request.method == 'POST':
      form.process(request.form)
      if form.validate():
        try:
          user = self.User.objects(email=form.email.data.lower()).get()
          send_mail(
            [user.email], 
            _('Reminder on how to login to Helmgast.se'),
            mail_type = 'remind_login',
            user=user
            )
          flash( _('Reminder email sent to your address'), 'success')
        except self.User.DoesNotExist:
          flash( _('No such user exist, are you sure you registered first?'), 'danger')
      else:
        flash( _('Errors in form'), 'danger')  
    return render_template('auth/remind.html', form=form)

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
    try:
      GOOGLE = build('plus', 'v1')
    except httplib2.ServerNotFoundError:
      self.logger.warning("Could not connect to Google")

    self.JoinForm = model_form(self.User, only=['password', 'email', 'username', 
      'email', 'realname', 'location', 'newsletter'], 
      field_args={ 'password':{'password':True} })
    self.JoinForm.confirm_password = PasswordField(label=_('Confirm Password'), 
        validators=[validators.Required(), validators.EqualTo('password', 
        message=_('Passwords must match'))])
    self.JoinForm.auth_code = HiddenField(_('Auth Code'))
    self.JoinForm.email_token = HiddenField(_('Email Token'))
    # We add these manually, because model_form will render them differently
    self.JoinForm.external_service = HiddenField(_('External Service'))

    self.LoginForm = model_form(self.User, only=['email', 'password'], field_args={'password':{'password':True}})
    self.LoginForm.auth_code = HiddenField(_('Auth Code'))
    self.LoginForm.external_service = HiddenField(_('External Service'))

    self.RemindForm = model_form(self.User, only=['email'])

    self.configure_routes()
    self.register_blueprint()
    self.register_handlers()
    self.register_context_processors()

