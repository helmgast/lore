from flask import Flask, Markup, flash, render_template
from flask_peewee.db import Database
from re import compile
from flaskext.markdown import Markdown
try:
    import simplejson as json
except ImportError:
    import json

app = Flask(__name__) # Creates new flask instance, named to app (this module)
app.config.from_object('config.Configuration') # Load config from config.py
db = Database(app) # Initiate the peewee DB layer
Markdown(app)

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

def generate_flash(action, name, model_identifiers, dest=''):
    s = '%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1 else '', ', '.join(model_identifiers), ' to %s' % dest if dest else '')
    flash(s, 'success')
    return s

def error_response(msg, level='error'):
    flash(msg, level)
    return render_template('includes/partial.html')