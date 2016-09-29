# import mongoengine.connection
# mongoengine.connection.old_get_connection = mongoengine.connection.get_connection

# def new_get_connection(alias='default', reconnect=False):
#   conn = mongoengine.connection.old_get_connection(alias, reconnect)
#   conn =
#   return False

# mongoengine.connection.get_connection = new_get_connection

import sys
import urllib

from datetime import datetime
from bson.objectid import ObjectId
from flask_mongoengine import Pagination, MongoEngine, DynamicDocument
from flask.json import JSONEncoder
from flask_debugtoolbar import DebugToolbarExtension
from markdown.treeprocessors import Treeprocessor
from mongoengine import Document, QuerySet, ConnectionError
from pymongo.errors import ConnectionFailure
from speaklater import _LazyString
from werkzeug.routing import Rule
from werkzeug.urls import url_decode
import time

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


class MethodRewriteMiddleware(object):
    """Rewrites POST with ending url /patch /put /delete into a proper PUT, PATCH, DELETE.
    Also removes the ending part of the url within flask, while user will see same URL"""

    def __init__(self, app):
        self.app = app

    # def __call__(self, environ, start_response):
    #     if environ['REQUEST_METHOD'] == 'POST':
    #         path = environ['PATH_INFO'].rsplit('/', 1)
    #         if len(path) > 1:
    #             intent = path[1].upper()
    #             print "Path %s in list = %s" % (intent, intent in ['PUT', 'PATCH', 'DELETE'])
    #             if intent in ['PUT', 'PATCH', 'DELETE']:
    #                 intent = intent.encode('ascii', 'replace')
    #                 environ['REQUEST_METHOD'] = intent
    #                 environ['PATH_INFO'] = path[0]
    #     return self.app(environ, start_response)

    def __call__(self, environ, start_response):
        if 'method' in environ.get('QUERY_STRING', ''):
            args = url_decode(environ['QUERY_STRING'])
            method = args.get('method', '').upper()
            if method and method in ['PUT', 'PATCH', 'DELETE']:
                method = method.encode('ascii', 'replace')
                environ['REQUEST_METHOD'] = method
        return self.app(environ, start_response)


class FablrRule(Rule):
    """Sorts rules starting with a variable, e.g. /<xyx>, last"""

    def match_compare_key(self):
        t = (self.rule.startswith('/<'),) + super(FablrRule, self).match_compare_key()
        return t


def db_config_string(app):
    # Clean to remove password
    return re.sub(r':([^/]+?)@', ':<REMOVED_PASSWORD>@', app.config['MONGODB_HOST'])


def is_db_empty(db):
    print db.collection_names(False)


db = MongoEngine()
# TODO this is a hack to turn of schema validation, as it reacts when database contains fields
# not in model, which can happen if we have a database that is used for branches with both new and old schema
# db.Document = DynamicDocument

# db.Document._meta['auto_create_index'] = False


def start_db(app):
    # while True:
    dbstring = db_config_string(app)
    db_config = {
        'MONGODB_SETTINGS': {
            'host': app.config['MONGODB_HOST'],
            'connectTimeoutMS': 50,
            'serverSelectionTimeoutMS': 50
        }
    }
    db.init_app(app, config=db_config)
    # try:
    with app.app_context():
        num_collections = len(db.connection.get_default_database().collection_names(False))
        if not app.debug and num_collections == 0:
            print >> sys.stderr, "Database %s is empty, run python manage.py db_setup" % dbstring
    # except ConnectionFailure as e:
    #     print >> sys.stderr, "Database connection failure %s: %s" % (e.__class__, e)
    #     exit(1)

        # break
        # except None:
        #     print >> sys.stderr, "Cannot connect to database: %s [waiting 20s]" % dbstring
        #     time.sleep(20)


class MongoJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Document) or isinstance(o, QuerySet):
            return o.to_mongo()
        elif isinstance(o, ObjectId) or isinstance(o, QuerySet):
            return str(o)
        elif isinstance(o, Pagination):
            return {'page': o.page, 'per_page': o.per_page, 'pages': o.pages, 'total': o.total}
        if isinstance(o, _LazyString):  # i18n Babel uses lazy strings, need to be treated as string here
            return unicode(o)
        return JSONEncoder.default(self, o)


from flask_babel import Babel

babel = Babel()

from flask import g, request, current_app, session


def get_locale():
    # If a route has set a different locale availability, we will take that from g object
    if 'available_locales' in g:
        locale = request.accept_languages.best_match(g.available_locales, current_app.config['BABEL_DEFAULT_LOCALE'])
        if 'locale' in request.args and request.args['locale'] in g.available_locales:
            locale = request.args['locale']
            session['locale'] = locale
        elif session.get('locale', None) in g.available_locales:
            locale = session.get('locale', None)  # If user have selected language
    else:
        locale = current_app.config.get('BABEL_DEFAULT_LOCALE', 'en')
    g.locale = locale
    # print "Got lang %s, available_locale %s" % (locale, g.available_locales)
    return locale


from flask_wtf.csrf import CsrfProtect

csrf = CsrfProtect()

from markdown.extensions import Extension
from markdown.inlinepatterns import ImagePattern, IMAGE_LINK_RE
from markdown.util import etree
import re


class GalleryList(Treeprocessor):
    def run(self, root):
        for ul in root.findall('ul'):
            if len(ul) and ul[0].text:
                h_text = ul[0].text.strip()
                if h_text in ['gallery-center', 'gallery-wide', 'gallery-side']:
                    ul.set('class', 'gallery %s' % h_text)
                    ul[0].set('class', 'hide')
                    for li in list(ul)[1:]:
                        li.set('class', 'gallery-item')
                        a_el = etree.Element('a')
                        a_el.set('href', '#')
                        a_el.set('class', 'zoomable')
                        a_el.extend(list(li))  # add all children of the list
                        for e in li:
                            li.remove(e)
                        li.append(a_el)
                        # imgs = list(ul.iterfind('.//img'))
                        # txts = list(ul.itertext())[1:]  # Skip first as it is the current node, e.g. ul
                        # # if there are same amount of images as text items, and the text is zero, we have only images in the list
                        # # however, they may be nested in other tags, e.g. a
                        # if ''.join(txts).strip() == '':  # All text nodes empty in the list


class NewImagePattern(ImagePattern):
    def handleMatch(self, m):
        el = super(NewImagePattern, self).handleMatch(m)
        alt = el.get('alt')
        src = el.get('src')
        # parts = alt.rsplit('|', 1)
        # el.set('alt', parts[0])
        # cl = parts[1] if len(parts) == 2 else None
        # if cl:
        #     el.set('class', cl)
        a_el = etree.Element('p')
        a_el.set('class', 'gallery')
        a_el.append(el)
        # a_el.set('href', src)
        return a_el


class AutolinkedImage(Extension):
    def extendMarkdown(self, md, md_globals):
        # Insert instance of 'mypattern' before 'references' pattern
        # md.inlinePatterns["image_link"] = NewImagePattern(IMAGE_LINK_RE, md)
        md.treeprocessors['gallery'] = GalleryList()


from jinja2 import Undefined


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        print 'JINJA2: something was undefined!'  # TODO, should print correct log error
        return None


def currentyear(nada):
    return datetime.utcnow().strftime('%Y')


def dict_without(value, *args):
    return {k: value[k] for k in value.keys() if k not in args}


def dict_with(value, **kwargs):
    z = value.copy()
    z.update(kwargs)
    return z
