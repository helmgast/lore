from flask import Flask
from flask_peewee.db import Database
from flask_peewee.auth import Auth
import os

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
        'user': 'admin',
        'password': 'xzUqQfsuJlhN',
        'host':'postgresql://%s:%s/' % (os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'],os.environ['OPENSHIFT_POSTGRESQL_DB_PORT']),
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