import subprocess as sp
import shlex
import os
from flask.ext.script import Manager
from fablr.app import create_app

os.environ['RACONTEUR_CONFIG_FILE'] = 'config.py'
app = create_app()
manager = Manager(app)

def runshell(cmd):
	retcode = sp.call(shlex.split(cmd))
	if retcode > 0:
		sys.exit(retcode) 

@manager.command
def lang_extract():
	print """
	Extract translatable strings and updates all .PO files.
	After running this, go to the .PO files and manually translate all empty MsgId
	then run python setup.py lang_compile
	"""
	runshell('pybabel extract --no-wrap -F fablr/translations/babel.cfg -o temp.pot fablr/')
	runshell('pybabel update -i temp.pot -d fablr/translations -l sv --no-fuzzy-matching')
	runshell('rm temp.pot')


@manager.command
def lang_compile():
	print """
	Compiles all .PO files to .MO so that they will show up at runtime.
	"""
	runshell('pybabel compile -d fablr/translations -l sv')

@manager.command
def db_setup():
  from mongoengine.connection import get_db

  app.logger.info("Resetting data models")
  print app.config['MONGODB_SETTINGS']
  db = get_db()
  # Drop all collections but not the full db as we'll lose user table then
  for c in db.collection_names(False):
    app.logger.info("Dropping collection %s" % c)
    db.drop_collection(c)
  from test_data import model_setup
  model_setup.setup_models()
  # This hack sets a unique index on the md5 of image files to prevent us from 
  # uploading duplicate images
  # db.connection[the_app.config['MONGODB_SETTINGS']['DB']]['images.files'].ensure_index(
 #        'md5', unique=True, background=True)

def validate_model():
  is_ok = True
  pkgs = ['model.campaign', 'model.misc', 'model.user', 'model.world']  # Look for model classes in these packages
  for doc in db.Document._subclasses:  # Ugly way of finding all document type
    if doc != 'Document':  # Ignore base type (since we don't own it)
      for pkg in pkgs:
        try:
          cls = getattr(__import__(pkg, fromlist=[doc]), doc)  # Do add-hoc import/lookup of type, simillar to from 'pkg' import 'doc'
          try:
            cls.objects()  # Check all objects of type
          except TypeError:
            logger.error("Failed to instantiate %s", cls)
            is_ok = False
        except AttributeError:
          pass  # Ignore errors from getattr
        except ImportError:
          pass  # Ignore errors from __import__
  logger.info("Model has been validated" if is_ok else "Model has errors, aborting startup")
  return is_ok

@manager.command
def import_csv():
  from tools import customer_data
  from mongoengine.connection import get_db

  app.logger.info("Importing customer data")
  print app.config['MONGODB_SETTINGS']
  get_db()
  customer_data.setup_customer()

@manager.command
def db_migrate():
  from tools import db_migration
  from mongoengine.connection import get_db

  db = get_db()
  db_migration.db_migrate(db)

@manager.command
def test():
  from tests import app_test

  logger.info("Running unit tests")
  app_test.run_tests()

if __name__ == "__main__":
    manager.run()