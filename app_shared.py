from flask import Flask
from flask_peewee.db import Database
from flask_peewee.auth import Auth

myapp = Flask(__name__) # Creates new flask instance, named to app (this module)
myapp.config.from_object('config.Configuration') # Load config from config.py
db = Database(myapp) # Initiate the peewee DB layer
from models import User
auth = Auth(myapp, db, user_model=User)