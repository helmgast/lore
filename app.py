import os, sys

import deploy
#
# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path
# 

from flask import Flask, Markup
from flask_peewee.auth import Auth
from flask_peewee.admin import Admin
from flask_peewee.db import Database
from re import compile
from flaskext.markdown import Markdown

try:
  import simplejson as json
except ImportError:
  import json

from app_shared import app, db, auth
from admin import create_admin
from api import create_api
from views import *

Markdown(app)

admin = create_admin(app, auth)
api = create_api(app, auth)

from world import world
from social import social
from generator import generator
from campaign import campaign

app.register_blueprint(world, url_prefix='/world')
app.register_blueprint(generator, url_prefix='/generator')
app.register_blueprint(social, url_prefix='/social')
app.register_blueprint(campaign, url_prefix='/campaign')

@app.template_filter('is_following')
def is_following(from_user, to_user):
    return from_user.is_following(to_user)
    
wikify_re = compile(r'\b(([A-Z]+[a-z]+){2,})\b')

@app.template_filter('wikify')
def wikify(s):
    return Markup(wikify_re.sub(r'<a href="/world/\1/">\1</a>', s))

@app.template_filter('dictreplace')
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

if __name__ == '__main__':
  if True:#'OPENSHIFT_INTERNAL_IP' in os.environ:
    deploy.run()
  else:
    print "Running local"
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
      print "Resetting data models"
      model_setup.setup_models()
      exit()
    app.run(debug=True) # Debug will reload code automatically, so no need to restart server