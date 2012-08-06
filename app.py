from flask import Flask, Markup
from flask_peewee.db import Database
from re import compile
from flaskext.markdown import Markdown

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