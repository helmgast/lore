"""
    raconteur.raconteur
    ~~~~~~~~~~~~~~~~

   Main raconteur application class, that initializes the Flask application,
   it's blueprints, plugins and template filters.

    :copyright: (c) 2014 by Raconteur
"""

from flask import Flask, Markup, render_template, request, redirect, url_for, flash
from datetime import datetime
from auth import Auth
from flask.ext.mongoengine import MongoEngine
from re import compile
from flaskext.markdown import Markdown
from flask.ext.mongoengine.wtf import model_form
from flask_wtf.csrf import CsrfProtect
# Babel
from flask.ext.babel import Babel
from config import LANGUAGES
import os
import logging

try:
  import simplejson as json
except ImportError:
  import json

the_app = None
db = None
auth = None

if the_app == None:
  from app import is_debug, is_deploy
  the_app = Flask('raconteur') # Creates new flask instance
  logger = logging.getLogger(__name__)
  logger.info("App created: %s", the_app)
  the_app.config.from_pyfile('config.cfg') # db-settings and secrets, should not be shown in code
  the_app.config['DEBUG'] = is_debug
  the_app.config['PROPAGATE_EXCEPTIONS'] = is_debug
  db = MongoEngine(the_app) # Initiate the MongoEngine DB layer
  # we can't import models before db is created, as the model classes are built on runtime knowledge of db
  
  from model.user import User

  auth = Auth(the_app, db, user_model=User)

  Markdown(the_app)
  CsrfProtect(the_app)
  babel = Babel(the_app)

  from controller.world import world_app as world
  from controller.social import social
  from controller.generator import generator
  from controller.campaign import campaign_app as campaign

  the_app.register_blueprint(world, url_prefix='/world')
  the_app.register_blueprint(generator, url_prefix='/generator')
  the_app.register_blueprint(social, url_prefix='/social')
  the_app.register_blueprint(campaign, url_prefix='/campaign')

def run_the_app(debug):
  logger.info("Running local instance")
  the_app.run(debug=debug)

from test_data import model_setup
def setup_models():
  logger = logging.getLogger(__name__)
  logger.info("Resetting data models")
  db.connection.drop_database(the_app.config['MONGODB_SETTINGS']['DB'])
  model_setup.setup_models()

from tests import app_test
def run_tests():
  logger = logging.getLogger(__name__)
  logger.info("Running unit tests")
  app_test.run_tests();


###
### Basic views (URL handlers)
###
@the_app.route('/')
def homepage():

  return render_template('homepage.html')
    #if auth.get_logged_in_user():
    #    return private_timeline()
    #else:
    #    return public_timeline()

JoinForm = model_form(User)

# Page to sign up, takes both GET and POST so that it can save the form
@the_app.route('/join/', methods=['GET', 'POST'])
def join():

    if request.method == 'POST' and request.form['username']:
        # Read username from the form that was posted in the POST request
        try:
            user = User.objects().get(username=request.form['username'])
            flash('That username is already taken')
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
    
wikify_re = compile(r'\b(([A-Z]+[a-z]+){2,})\b')

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
        for i in range(1,len(parts),2):
            parts[i] = d[parts[i]] # Replace with dict content
        return ''.join(parts)
    return s
    
# i18n
@babel.localeselector
def get_locale():
    return "sv"#request.accept_languages.best_match(LANGUAGES.keys()) # Add 'sv' here instead to force swedish translation.
