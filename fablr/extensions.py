# import mongoengine.connection
# mongoengine.connection.old_get_connection = mongoengine.connection.get_connection

# def new_get_connection(alias='default', reconnect=False):
#   conn = mongoengine.connection.old_get_connection(alias, reconnect)
#   conn =
#   return False

# mongoengine.connection.get_connection = new_get_connection

from flask.json import JSONEncoder
from bson.objectid import ObjectId
from mongoengine import Document, QuerySet, ConnectionError
from flask.ext.mongoengine import Pagination, MongoEngine, DynamicDocument
from flask_debugtoolbar import DebugToolbarExtension
import sys
import re

toolbar = DebugToolbarExtension()
# class MyMongoEngine(MongoEngine):
  # def

  # def get_db(alias='default', reconnect=False):
  #   global _dbs
  #   if reconnect:
  #     disconnect(alias)

  #   if alias not in _dbs:
  #     conn = get_connection(alias)
  #     conn_settings = _connection_settings[alias]
  #     db = conn[conn_settings['name']]
  #     # Authenticate if necessary
  #     if conn_settings['username'] and conn_settings['password']:
  #       db.authenticate(conn_settings['username'], conn_settings['password'],
  #         source=conn_settings['auth_source'])
  #     _dbs[alias] = db
  #   print "Using get_db"
  #   return _dbs[alias]


from werkzeug import url_decode

class MethodRewriteMiddleware(object):
    """Rewrites POST with ending url /patch /put /delete into a proper PUT, PATCH, DELETE.
    Also removes the ending part of the url within flask, while user will see same URL"""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'POST':
            path = environ['PATH_INFO'].rsplit('/',1)
            if len(path)>1:
                intent = path[1].upper()
                print "Path %s in list = %s" % (intent, intent in ['PUT', 'PATCH', 'DELETE'])
                if intent in ['PUT', 'PATCH', 'DELETE']:
                    intent = intent.encode('ascii', 'replace')
                    environ['REQUEST_METHOD'] = intent
                    environ['PATH_INFO'] = path[0]
        return self.app(environ, start_response)

def db_config_string(app):
   # Clean to remove password
  return re.sub(r':([^/]+?)@',':<REMOVED_PASSWORD>@', app.config['MONGODB_HOST'])

def is_db_empty(db):
  print db.collection_names(False)
db = MongoEngine()
# TODO this is a hack to turn of schema validation, as it reacts when database contains fields
# not in model, which can happen if we have a database that is used for branches with both new and old schema
db.Document = DynamicDocument

def start_db(app):
  try:
    db.init_app(app)
  except ConnectionError:
    dbstring = db_config_string(app)
    print >> sys.stderr, "Cannot connect to database: %s" % dbstring
    raise
    exit(1)
  if not app.debug and len(db.connection.get_default_database().collection_names(False)) == 0:
    print >> sys.stderr, "Database is empty, run python manage.py db_setup"
    exit(1)

class MongoJSONEncoder(JSONEncoder):
  def default(self, o):
    if isinstance(o, Document) or isinstance(o, QuerySet):
      return o.to_mongo()
    elif isinstance(o, ObjectId) or isinstance(o, QuerySet):
      return str(o)
    elif isinstance(o, Pagination):
      return {'page':o.page, 'per_page':o.per_page, 'total':o.total}
    print JSONEncoder.default(self, o)
    return JSONEncoder.default(self, o)

from flask.ext.babel import Babel
babel = Babel()

from flask import g
def get_locale():
  # if a user is logged in, use the locale from the user settings
  # user = getattr(g, 'user', None)
  # if user is not None:
  #   return user.locale
  # otherwise try to guess the language from the user accept
  # header the browser transmits.  We support de/fr/en in this
  # example.  The best match wins.
  # return request.accept_languages.best_match(['de', 'fr', 'en'])
  # print "Returning get_locate %s" % 'en'
  return getattr(g, 'lang', 'sv')

#i18n
# @babel.localeselector
# def get_locale():
#   return "sv"  # request.accept_languages.best_match(LANGUAGES.keys()) # Add 'sv' here instead to force swedish translation.
# Needs below in Config
# LANGUAGES = {
#    'en': 'English',
#    'sv': 'Swedish'
#}

from flask_wtf.csrf import CsrfProtect
csrf = CsrfProtect()

from flaskext.markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import ImagePattern, IMAGE_LINK_RE
from markdown.util import etree
import re

class NewImagePattern(ImagePattern):
  def handleMatch(self, m):
    el = super(NewImagePattern, self).handleMatch(m)
    alt = el.get('alt')
    src = el.get('src')
    parts = alt.rsplit('|',1)
    el.set('alt',parts[0])
    cl = parts[1] if len(parts)==2 else None
    # if not re.match(r'http(s)?://|data',src):
    #     src = ('/asset/image/thumbs/' if cl in ['gallery', 'thumb'] else '/asset/image/')+src
    #     el.set('src', src)
    if cl:
        el.set('class', cl)
    a_el = etree.Element('a')
    a_el.set('class', 'lightbox')
    a_el.append(el)
    a_el.set('href', src)
    return a_el

class AutolinkedImage(Extension):
  def extendMarkdown(self, md, md_globals):
    # Insert instance of 'mypattern' before 'references' pattern
    md.inlinePatterns["image_link"] = NewImagePattern(IMAGE_LINK_RE, md)

from jinja2 import Undefined

class SilentUndefined(Undefined):
  def _fail_with_undefined_error(self, *args, **kwargs):
    print 'JINJA2: something was undefined!' #TODO, should print correct log error
    return None
