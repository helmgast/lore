import subprocess as sp
import shlex
import os
from flask.ext.script import Manager, prompt_pass
from fablr.app import create_app
from fablr.controller.pdf import fingerprint_pdf, get_fingerprints, fingerprint_from_user

os.environ['RACONTEUR_CONFIG_FILE'] = 'config.py'
app = create_app(no_init=True) # delay initializaiton to avoid database etc
manager = Manager(app)

def runshell(cmd):
	retcode = sp.call(shlex.split(cmd))
	if retcode > 0:
		sys.exit(retcode)

@manager.command
def lang_extract():
	"""Extract translatable strings and .PO files for predefined locales (SV).
	After running this, go to the .PO files in fablr/translations/ and manually
	translate all empty MsgId. Then run python manage.py lang_compile
	"""
	runshell('pybabel extract --no-wrap -F fablr/translations/babel.cfg -o temp.pot fablr/')
	runshell('pybabel update -i temp.pot -d fablr/translations -l sv --no-fuzzy-matching')
	runshell('rm temp.pot')

@manager.command
def lang_compile():
	"""Compiles all .PO files to .MO so that they will show up at runtime."""

	runshell('pybabel compile -d fablr/translations -l sv')

@manager.option('--reset',  dest='reset', action='store_true', default=False, help='Reset database, WILL DESTROY DATA')
def db_setup(reset=False):
  """Setup a new database with starting data"""
  from mongoengine.connection import get_db
  from fablr.extensions import db_config_string
  print db_config_string
  db = get_db()

  # Check if DB is empty
    # If empty, insert an admin user and a default world
  from model.user import User, UserStatus
  if len(User.objects(admin=True))==0: # consider the database empty
    admin_password = app.config['SECRET_KEY']
    admin_email = app.config['MAIL_DEFAULT_SENDER']
    print dict(username='admin',
      password="<SECRET KEY FROM CONFIG>",
      email=app.config['MAIL_DEFAULT_SENDER'],
      admin=True,
      status=UserStatus.active)

    u = User(username='admin',
      password=the_app.config['SECRET_KEY'],
      email=the_app.config['MAIL_DEFAULT_SENDER'],
      admin=True,
      status=UserStatus.active)
    u.save()
    World.create(title="Helmgast") # Create the default world

  # Else, if reset, drop all collections
  elif reset:
    # Drop all collections but not the full db as we'll lose user table then
    for c in db.collection_names(False):
      app.logger.info("Dropping collection %s" % c)
      db.drop_collection(c)
    from tools.test_data import model_setup
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
  """Run all unit tests on Fablr"""
  from tests import app_test
  import unittest
  suite = unittest.TestLoader().loadTestsFromTestCase(app_test.FablrTestCase)
  unittest.TextTestRunner(verbosity=2).run(suite)

@manager.option('email', help='Set a new password)')
def set_password(email):
  if not app.debug:
    print "We don't allow changing passwords if not in debug mode"
    exit(1)
  from fablr.model.user import User
  user = User.objects(email=email).first()
  if user:
    passw = prompt_pass("Enter the new password")
    if passw and len(passw) > 4:
      user.password = passw
      user.save()
    else:
      print "Too short or no password provided"
  else:
    print "No such user"

@manager.option('file', help='The file to upload to the database')
@manager.option('--title', dest="title", action='store', help='Title of the file')
@manager.option('--desc', dest="desc", action='store', help='Description of the file')
@manager.option('--access', dest="access", action='store', help='Access type, either public, product or user')
def file_upload(file, title, desc, access):
  """Adds a file asset from command line to the GridFS database"""
  from fablr.model.asset import FileAsset, FileAccessType
  import mimetypes

  if not file or not os.access(file, os.R_OK): # check read access
    raise ValueError("File %s not readable" % file)

  access = access if access in FileAccessType else 'public'
  fname = os.path.basename(file)
  if not title:
    title = fname
  fa = FileAsset(
  	title=title,
  	description=desc,
	source_filename=fname,
	attachment_filename=fname,
	access_type=access)
  mime = mimetypes.guess_type(fname)[0]
  fa.file_data.put(open(file), filename=fname, content_type=mime)
  fa.save()
  print file, title, desc
  # print file, title, description


@manager.option('output', help='File path to write new PDF to')
@manager.option('input', help='PDF file to fingerprint (will not change input)')
@manager.option('--user', dest="user_id", help='User ID to fingerprint with', required=True)
def pdf_fingerprint(input, output, user_id):
  """Will manually fingerprint a PDF file."""
  print "Fingerprinting user %s from file %s into file %s" % (user_id, input, output)
  with open(output, 'wb') as f:
    with open(input, 'rb') as f2:
      for buf in fingerprint_pdf(f2, user_id):
        f.write(buf)

@manager.option('input', help='PDF file to check for fingerprints')
def pdf_check(input):
  """Will scan a PDF for matching fingerprints"""
  fps = get_fingerprints(input)
  from fablr.model.user import User
  users = list(User.objects().only('id', 'username'))
  # users.append('ripperdoc@gmail.com')
  # print users
  for user in users:
    uid = fingerprint_from_user(user.id)
    print "User %s with id %s got fp %s" % (user, user.id, uid)
    for fp in fps:
      if uid == fp:
        print "User %s matches fingerprint %s in document %s" % (user, fp, input)
        exit(1)
  print "No match for any user in document %s" % (input)

if __name__ == "__main__":
    manager.run()
