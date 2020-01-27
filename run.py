import sys
import os
import re
import click
import shlex
import subprocess as sp

from flask.cli import pass_script_info, DispatchingApp
from flask.helpers import get_debug_flag

from lore.app import create_app
app = create_app()

def runshell(cmd):
    cmdsplit = shlex.split(cmd)
    cp = sp.run(cmdsplit)
    if cp.returncode > 0:
        sys.exit(cp.returncode)

@app.cli.command()
def initdb():
    """Initialize the database."""
    click.echo('Init the db')

# @app.cli.command()
# @click.option('--host', '-h', default='127.0.0.1',
#               help='The interface to bind to.')
# @click.option('--port', '-p', default=5000,
#               help='The port to bind to.')
# @click.option('--reload/--no-reload', default=None,
#               help='Enable or disable the reloader.  By default the reloader '
#               'is active if debug is enabled.')
# @click.option('--debugger/--no-debugger', default=None,
#               help='Enable or disable the debugger.  By default the debugger '
#               'is active if debug is enabled.')
# @click.option('--eager-loading/--lazy-loader', default=None,
#               help='Enable or disable eager loading.  By default eager '
#               'loading is enabled if the reloader is disabled.')
# @click.option('--with-threads/--without-threads', default=False,
#               help='Enable or disable multithreading.')
# @click.option('--watch', default=None, multiple=True,
#               help='Add files to watch for reload')
# @pass_script_info
# def runwatch(info, host, port, reload, debugger, eager_loading,
#                 with_threads, watch):
#     from werkzeug.serving import run_simple

#     debug = get_debug_flag()
#     if reload is None:
#         reload = bool(debug)
#     if debugger is None:
#         debugger = bool(debug)
#     if eager_loading is None:
#         eager_loading = not reload

#     app = DispatchingApp(info.load_app, use_eager_loading=eager_loading)

#     # Extra startup messages.  This depends a bit on Werkzeug internals to
#     # not double execute when the reloader kicks in.
#     if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
#         # If we have an import path we can print it out now which can help
#         # people understand what's being served.  If we do not have an
#         # import path because the app was loaded through a callback then
#         # we won't print anything.
#         if info.app_import_path is not None:
#             print(' * Serving Flask app "%s"' % info.app_import_path)
#         if debug is not None:
#             print(' * Forcing debug mode %s' % (debug and 'on' or 'off'))

#     run_simple(host, port, app, use_reloader=reload,
#                use_debugger=debugger, threaded=with_threads, extra_files=watch)

@app.cli.command()
def lang_extract(): # Run as lang-extract
    """Extract translatable strings and .PO files for predefined locales (SV).
    After running this, go to the .PO files in lore/translations/ and manually
    translate all empty MsgId. Then run python manage.py lang_compile
    """

    runshell('.venv/bin/pybabel extract --no-wrap --sort-by-file -F lore/translations/babel.cfg -o temp.pot lore/ plugins/')
    runshell('.venv/bin/pybabel update -i temp.pot -d lore/translations -l sv --no-fuzzy-matching')
    runshell('rm temp.pot')
    print()
    print("New strings needing translation:")
    print("------------------------")
    with open('lore/translations/sv/LC_MESSAGES/messages.po') as f:
        s = f.read()
        for m in re.findall(r'msgid ((".*"\s+)+)msgstr ""\s\s', s):
            print(m[0].split('/n')[0])  # avoid too long ones

@app.cli.command()
def lang_compile(): # Run as lang-compile
    """Compiles all .PO files to .MO so that they will show up at runtime."""

    runshell('pybabel compile -d lore/translations -l sv')


@app.cli.command()
@click.option('--reset', default=False, help='Reset database, WILL DESTROY DATA')
def db_setup(reset=False):
    """Setup a new database with starting data"""
    from mongoengine.connection import get_db
    from lore.extensions import db_config_string
    print(db_config_string)
    db = get_db()
    # Check if DB is empty
    # If empty, insert an admin user and a default world
    from model.user import User, UserStatus
    if len(User.objects(admin=True)) == 0:  # consider the database empty
        admin_password = app.config['SECRET_KEY']
        admin_email = app.config['MAIL_DEFAULT_SENDER']
        print(dict(username='admin',
                   password="<SECRET KEY FROM CONFIG>",
                   email=app.config['MAIL_DEFAULT_SENDER'],
                   admin=True,
                   status=UserStatus.active))

        u = User(username='admin',
                 password=app.config['SECRET_KEY'],
                 email=app.config['MAIL_DEFAULT_SENDER'],
                 admin=True,
                 status=UserStatus.active)
        u.save()
        World.create(title="Helmgast")  # Create the default world

    # Else, if reset, drop all collections
    elif reset:
        # Drop all collections but not the full db as we'll lose user table then
        for c in db.collection_names(False):
            app.logger.info("Dropping collection %s" % c)
            db.drop_collection(c)
        from tools.dummy_data import model_setup
        model_setup.setup_models()

        # This hack sets a unique index on the md5 of image files to prevent us from
        # uploading duplicate images
        # db.connection[the_app.config['MONGODB_SETTINGS']['DB']]['images.files'].ensure_index(
        #        'md5', unique=True, background=True)

@app.cli.command()
def validate_model():
    is_ok = True
    pkgs = ['model.misc', 'model.user', 'model.world']  # Look for model classes in these packages
    for doc in Document._subclasses:  # Ugly way of finding all document type
        if doc != 'Document':  # Ignore base type (since we don't own it)
            for pkg in pkgs:
                try:
                    cls = getattr(__import__(pkg, fromlist=[doc]),
                                  doc)  # Do add-hoc import/lookup of type, simillar to from 'pkg' import 'doc'
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


@app.cli.command()
def import_csv():
    from tools import customer_data
    from mongoengine.connection import get_db
    app.logger.info("Importing customer data")
    print(app.config['MONGODB_SETTINGS'])
    get_db()
    customer_data.setup_customer()

@app.cli.command()
@click.option('-s','--sheet', required=False, help='Name or index of worksheet, if URL lacks #gid=x parameter')
@click.option('-m','--model', required=True, help='Name of model to import to/with')
@click.option('-r','--repeat_on_empty', is_flag=True, help='If a cell is empty in a row with data, repeat value from row above')
@click.option('-c','--commit', is_flag=True, help='If given, will commit import. Otherwise just print the first 10 results.')
@click.option('--maxrows', default=10, type=int, help='Maximum amounts of rows to process')
@click.argument('url_or_id', required=True)
def import_sheet(url_or_id, sheet, model, repeat_on_empty, commit, maxrows):
    from tools.sheets_importer import import_data
    from mongoengine.connection import get_db
    from lore import extensions
    extensions.db.init_app(app)
    db = get_db()
    if maxrows < 1:
        maxrows = 1000000 # Just a high number
    import_data(url_or_id, sheet, model, repeat_on_empty, commit, maxrows)


@app.cli.command()
def db_migrate():
    from tools import db_migration
    from mongoengine.connection import get_db
    from lore import extensions
    extensions.db.init_app(app)
    db = get_db()
    # Ensure we have both app context and a (dummy) request context
    with app.app_context():
        with app.test_request_context('/'):
            db_migration.db_migrate(db)


@app.cli.command()
def test():
    """Run all unit tests on Lore"""
    from tests import app_test
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(app_test.LoreTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)


@app.cli.command()
@click.option('--email', help='Set a new password)')
def set_password(email):
    if not app.debug:
        print("We don't allow changing passwords if not in debug mode")
        exit(1)
    from lore.model.user import User
    user = User.query_user_by_email(email=email).first()
    if user:
        passw = prompt_pass("Enter the new password")
        if passw and len(passw) > 4:
            user.password = passw
            user.save()
        else:
            print("Too short or no password provided")
    else:
        print("No such user")


@app.cli.command()
@click.option('--file', help='The file to upload to the database')
@click.option('--title', help='Title of the file')
@click.option('--desc', help='Description of the file')
@click.option('--access', help='Access type, either public, product or user')
def file_upload(file, title, desc, access):
    """Adds a file asset from command line to the GridFS database"""
    from lore.model.asset import FileAsset, FileAccessType
    import mimetypes

    if not file or not os.access(file, os.R_OK):  # check read access
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
    print(file, title, desc)
    # print file, title, description


@app.cli.command()
@click.option('--output', help='File path to write new PDF to')
@click.option('--input', help='PDF file to fingerprint (will not change input)')
@click.option('--user', help='User ID to fingerprint with', required=True)
def pdf_fingerprint(input, output, user):
    """Will manually fingerprint a PDF file."""
    print("Fingerprinting user %s from file %s into file %s" % (user, input, output))
    with open(output, 'wb') as f:
        with open(input, 'rb') as f2:
            for buf in fingerprint_pdf(f2, user):
                f.write(buf)

@app.cli.command()
@click.option('--input', help='PDF file to check for fingerprints')
def pdf_check(input):
    """Will scan a PDF for matching fingerprints"""
    fps = get_fingerprints(input)
    from lore.model.user import User
    users = list(User.objects().only('id', 'username'))
    # users.append('ripperdoc@gmail.com')
    # print users
    for user in users:
        uid = fingerprint_from_user(user.id)
        print("User %s with id %s got fp %s" % (user, user.id, uid))
        for fp in fps:
            if uid == fp:
                print("User %s matches fingerprint %s in document %s" % (user, fp, input))
                exit(1)
    print("No match for any user in document %s" % (input))