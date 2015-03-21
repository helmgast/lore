# import mongoengine.connection
# mongoengine.connection.old_get_connection = mongoengine.connection.get_connection

# def new_get_connection(alias='default', reconnect=False):
#   conn = mongoengine.connection.old_get_connection(alias, reconnect)
#   conn = 
#   return False

# mongoengine.connection.get_connection = new_get_connection

from flask.json import JSONEncoder
from bson.objectid import ObjectId
from mongoengine import Document, QuerySet
from flask.ext.mongoengine import Pagination, MongoEngine

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


db = MongoEngine()

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

class NewImagePattern(ImagePattern):
  def handleMatch(self, m):
    el = super(NewImagePattern, self).handleMatch(m)
    alt = el.get('alt')
    src = el.get('src')
    parts = alt.rsplit('|',1)
    el.set('alt',parts[0])
    if len(parts)==2:
      el.set('class', parts[1])
      if parts[1] in ['gallery', 'thumb']:
        el.set('src', src.replace('/asset/','/asset/thumbs/'))
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
