
from flask import Flask, Markup, render_template, request, redirect, url_for, flash
from datetime import datetime
from auth import Auth
from flask.ext.mongoengine import MongoEngine
from re import compile
from flaskext.markdown import Markdown
import os

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
  print "App created"
  print the_app
  the_app.config.from_pyfile('dbconfig.cfg') # db-settings, should not be shown in code
  the_app.config['DEBUG'] = is_debug
  the_app.config['PROPAGATE_EXCEPTIONS'] = is_debug
  db = MongoEngine(the_app) # Initiate the MongoEngine DB layer
  # we can't import models before db is created, as the model classes are built on runtime knowledge of db
  
  # import model_setup
  from model.user import User

  auth = Auth(the_app, db, user_model=User)

  Markdown(the_app)

#   from world import world_app as world
  from social import social
#   from generator import generator
#   from campaign import campaign

#   the_app.register_blueprint(world, url_prefix='/world')
#   the_app.register_blueprint(generator, url_prefix='/generator')
  the_app.register_blueprint(social, url_prefix='/social')
#   the_app.register_blueprint(campaign, url_prefix='/campaign')
  #print the_app.url_map
  
from test_data import model_setup
def setup_models():
  model_setup.setup_models()

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

# Page to sign up, takes both GET and POST so that it can save the form
@the_app.route('/join/', methods=['GET', 'POST'])
def join():
    if request.method == 'POST' and request.form['username']:
        # Read username from the form that was posted in the POST request
        try:
            user = User.get(username=request.form['username'])
            flash('That username is already taken')
        except User.DoesNotExist:
            user = User(
                username=request.form['username'],
                email=request.form['email'],
                join_date=datetime.datetime.now()
            )
            user.set_password(request.form['password'])
            user.save()
            
            auth.login_user(user)
            return redirect(url_for('homepage'))

    return render_template('join.html')

###
### Template filters
###
@the_app.template_filter('is_following')
def is_following(from_user, to_user):
    return from_user.is_following(to_user)
    
wikify_re = compile(r'\b(([A-Z]+[a-z]+){2,})\b')

@the_app.template_filter('wikify')
def wikify(s):
    return Markup(wikify_re.sub(r'<a href="/world/\1/">\1</a>', s))

@the_app.template_filter('dictreplace')
def dictreplace(s, d):
    #print "Replacing %s with %s" % (s,d)
    if d and len(d) > 0:
        parts = s.split("__")
        # Looking for variables __key__ in s.
        # Splitting on __ makes every 2nd part a key, starting with index 1 (not 0)
        for i in range(1,len(parts),2):
            parts[i] = d[parts[i]] # Replace with dict content
        return ''.join(parts)
    return s