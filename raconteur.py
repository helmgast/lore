"""
  raconteur.raconteur
  ~~~~~~~~~~~~~~~~

  Main raconteur application class, that initializes the Flask application,
  it's blueprints, plugins and template filters.

  :copyright: (c) 2014 by Raconteur
"""

import logging
from re import compile
from flask import Flask, Markup, render_template, request, redirect, url_for, flash, g
from auth import Auth
# from admin import Admin

from flask.json import JSONEncoder, jsonify
from flask.ext.mongoengine import MongoEngine
from flask.ext.mongoengine.wtf import model_form
from flaskext.markdown import Markdown
from flask_wtf.csrf import CsrfProtect
# Babel
from flask.ext.babel import Babel
from flask.ext.babel import lazy_gettext as _
from mongoengine import Document, QuerySet
from markdown.extensions import Extension
from markdown.inlinepatterns import ImagePattern, IMAGE_LINK_RE
from markdown.util import etree

class MongoJSONEncoder(JSONEncoder):
  def default(self, o):
    if isinstance(o, Document) or isinstance(o, QuerySet):
      return o.to_json()
    return JSONEncoder.default(self, o)

class NewImagePattern(ImagePattern):
  def handleMatch(self, m):
    el = super(NewImagePattern, self).handleMatch(m)
    alt = el.get('alt')
    src = el.get('src')
    parts = alt.rsplit('|',1)
    if len(parts)==2:
      el.set('alt',parts[0])
      el.set('class', parts[1])
    el.set('src', src.replace('/images/','/images/thumbs/'))
    a_el = etree.Element('a')
    a_el.append(el)
    a_el.set('href', src)
    return a_el

class AutolinkedImage(Extension):
    def extendMarkdown(self, md, md_globals):
        # Insert instance of 'mypattern' before 'references' pattern
        md.inlinePatterns["image_link"] = NewImagePattern(IMAGE_LINK_RE, md)

the_app = None
db = None
auth = None

# Private = Everything locked down, no access to database (due to maintenance)
# Protected = Site is fully visible. Resources are shown on a case-by-case (depending on default access allowance). Admin is allowed to log in.
# Public = Everyone is allowed to log in and create new accounts
STATE_PRIVATE, STATE_PROTECTED, STATE_PUBLIC = 0, 1, 2
app_state = STATE_PUBLIC

app_features = {
  "tools": False,
  "join": True
}


def is_private():
  return app_state == STATE_PRIVATE


def is_protected():
  return app_state == STATE_PROTECTED


def is_public():
  return app_state == STATE_PUBLIC


def is_allowed_access(user):
  if is_private():
    return False
  elif is_protected():
    return user.admin if user else False
  else:
    return True

if the_app is None:
  from app import is_debug

  the_app = Flask('raconteur')  # Creates new flask instance
  logger = logging.getLogger(__name__)
  logger.info("App created: %s", the_app)
  the_app.config.from_pyfile('config.py')  # db-settings and secrets, should not be shown in code
  the_app.config['DEBUG'] = is_debug
  the_app.config['PROPAGATE_EXCEPTIONS'] = is_debug
  the_app.json_encoder = MongoJSONEncoder
  db = MongoEngine(the_app)  # Initiate the MongoEngine DB layer
  # we can't import models before db is created, as the model classes are built on runtime knowledge of db

  from model.user import User

  auth = Auth(the_app, db, user_model=User)
#  admin = Admin(the_app, auth)

  md = Markdown(the_app)
  md.register_extension(AutolinkedImage)
  csrf = CsrfProtect(the_app)
  babel = Babel(the_app)

  from controller.world import world_app as world
  from controller.social import social
  from controller.generator import generator
  from controller.campaign import campaign_app as campaign
  from resource import ResourceError

  the_app.register_blueprint(world, url_prefix='/world')
  if app_features["tools"]:
    the_app.register_blueprint(generator, url_prefix='/generator')
  the_app.register_blueprint(social, url_prefix='/social')
  the_app.register_blueprint(campaign, url_prefix='/campaign')

JoinForm = model_form(User)
wikify_re = compile(r'\b(([A-Z]+[a-z]+){2,})\b')


@the_app.before_request
def load_user():
  g.feature = app_features

def run_the_app(debug):
  logger.info("Running local instance")
  the_app.run(debug=debug)


def setup_models():
  logger.info("Resetting data models")
  db.connection.drop_database(the_app.config['MONGODB_SETTINGS']['DB'])
  from test_data import model_setup
  model_setup.setup_models()
  # This hack sets a unique index on the md5 of image files to prevent us from 
  # uploading duplicate images
  # db.connection[the_app.config['MONGODB_SETTINGS']['DB']]['images.files'].ensure_index(
 #        'md5', unique=True, background=True)


def validate_model():
  is_ok = True
  pkgs = ['model.campaign', 'model.misc', 'model.user', 'model.world']  # Look for model classes in these packages
  for doc in db.Document._subclasses:  # Ugly way of finding all document type
    if doc != 'Document':  # Ignore base type (since we don't own it)
      for pkg in pkgs:
        try:
          cls = getattr(__import__(pkg, fromlist=[doc]), doc)  # Do add-hoc import/lookup of type, simillar to from 'pkg' import 'doc'
          try:
            cls.objects()  # Check all objects of type
          except TypeError:
            logger.error("Failed to instantiate %s", cls)
            is_ok = False
        except AttributeError:
          pass  # Ignore errors from getattr
        except ImportError:
          pass  # Ignore errors from __import__
  logger.info("Model has been validated" if is_ok else "Model has errors, aborting startup")
  return is_ok


def run_tests():
  logger.info("Running unit tests")
  from tests import app_test
  app_test.run_tests()

if not is_debug:
  @the_app.errorhandler(ResourceError)
  def handle_invalid_usage(error):
      response = jsonify(error.to_dict())
      print request.args
      return response


###
### Basic views (URL handlers)
###
@the_app.route('/')
def homepage():
  return render_template('homepage.html')


@auth.admin_required
@the_app.route('/admin/', methods=['GET', 'POST'])
def admin():
  if request.method == 'POST' and request.form['state']:
    pass
  return render_template('maintenance.html')


# Page to sign up, takes both GET and POST so that it can save the form
@the_app.route('/join/', methods=['GET', 'POST'])
def join():
  if not app_features["join"]:
    raise ResourceError(403)
  if request.method == 'POST' and request.form['username']:
    # Read username from the form that was posted in the POST request
    try:
      User.objects().get(username=request.form['username'])
      flash(_('That username is already taken'))
    except User.DoesNotExist:
      user = User(
          username=request.form['username'],
          email=request.form['email'],
      )
      user.set_password(request.form['password'])
      user.save()

      auth.login_user(user)
      return redirect(url_for('homepage'))
  join_form = JoinForm()
  return render_template('join.html', join_form=join_form)


###
### Template filters
###
@the_app.template_filter('is_following')
def is_following(from_user, to_user):
    return from_user.is_following(to_user)


@the_app.template_filter('wikify')
def wikify(s):
    if s:
      return Markup(wikify_re.sub(r'<a href="/world/\1/">\1</a>', s))
    else:
      return ""


@the_app.template_filter('dictreplace')
def dictreplace(s, d):
    if d and len(d) > 0:
        parts = s.split("__")
        # Looking for variables __key__ in s.
        # Splitting on __ makes every 2nd part a key, starting with index 1 (not 0)
        for i in range(1, len(parts), 2):
            parts[i] = d[parts[i]]  # Replace with dict content
        return ''.join(parts)
    return s


# i18n
@babel.localeselector
def get_locale():
    return "sv"  # request.accept_languages.best_match(LANGUAGES.keys()) # Add 'sv' here instead to force swedish translation.
