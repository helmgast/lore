from flask import Flask
from flask_peewee.db import Database
from flask_peewee.auth import Auth

class LocalConfiguration(object):
    DATABASE = {
        'name': 'example.db',
        'engine': 'peewee.SqliteDatabase',
        'check_same_thread': False,
    }
    DEBUG = True
    SECRET_KEY = 'shhhh'

class DeployConfiguration(object):
    DATABASE = {
        'user': 'martin',
        'password': 'admin',
        'host':'127.0.0.1',
        'name': 'raconteur',
        'engine': 'peewee.PostgresqlDatabase',
        'threadlocals': True,
        #'check_same_thread': False,
    }
    DEBUG = True
    SECRET_KEY = 'shhhh'

myapp = Flask('raconteur') # Creates new flask instance, named to app (this module)
myapp.config.from_object(__name__+'.DeployConfiguration') # Load config from config.py
db = Database(myapp) # Initiate the peewee DB layer
from models import User
auth = Auth(myapp, db, user_model=User)