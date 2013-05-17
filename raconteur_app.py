
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

from app_shared import myapp, db, auth
from admin import create_admin
from api import create_api
from views import *

Markdown(myapp)

admin = create_admin(myapp, auth)
api = create_api(myapp, auth)

from world import world
from social import social
from generator import generator
from campaign import campaign

myapp.register_blueprint(world, url_prefix='/world')
myapp.register_blueprint(generator, url_prefix='/generator')
myapp.register_blueprint(social, url_prefix='/social')
myapp.register_blueprint(campaign, url_prefix='/campaign')

@myapp.template_filter('is_following')
def is_following(from_user, to_user):
    return from_user.is_following(to_user)
    
wikify_re = compile(r'\b(([A-Z]+[a-z]+){2,})\b')

@myapp.template_filter('wikify')
def wikify(s):
    return Markup(wikify_re.sub(r'<a href="/world/\1/">\1</a>', s))

@myapp.template_filter('dictreplace')
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