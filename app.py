# from flask import Flask, Markup, flash
# from flask_peewee.db import Database
# from re import compile
# from flaskext.markdown import Markdown

# try:
#     import simplejson as json
# except ImportError:
#     import json

# app = Flask(__name__) # Creates new flask instance, named to app (this module)
# app.config.from_object('config.Configuration') # Load config from config.py
# db = Database(app) # Initiate the peewee DB layer
# Markdown(app)

# @app.template_filter('is_following')
# def is_following(from_user, to_user):
#     return from_user.is_following(to_user)
    
# wikify_re = compile(r'\b(([A-Z]+[a-z]+){2,})\b')

# @app.template_filter('wikify')
# def wikify(s):
#     return Markup(wikify_re.sub(r'<a href="/world/\1/">\1</a>', s))

# @app.template_filter('dictreplace')
# def dictreplace(s, d):
#     #print "Replacing %s with %s" % (s,d)
#     if d and len(d) > 0:
#         parts = s.split("__")
#         # Looking for variables __key__ in s.
#         # Splitting on __ makes every 2nd part a key, starting with index 1 (not 0)
#         for i in range(1,len(parts),2):
#             parts[i] = d[parts[i]] # Replace with dict content
#         return ''.join(parts)
#     return s
#!/usr/bin/env python
import imp
import os
import sys

import deploy


#
# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path
# 


#
#  main():
#
if __name__ == '__main__':
   ip   = os.environ['OPENSHIFT_INTERNAL_IP']
   port = 8080
   zapp = imp.load_source('application', 'wsgi/application')

   #  Use gevent if we have it, otherwise run a simple httpd server.
   print 'Starting WSGIServer on %s:%d ... ' % (ip, port)
   try:
      deploy.run_gevent_server(zapp.application, ip, port)
   except:
      print 'gevent probably not installed - using default simple server ...'
      deploy.run_simple_httpd_server(zapp.application, ip, port)