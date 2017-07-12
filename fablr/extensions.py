from __future__ import print_function
from builtins import str
from builtins import object
import re
import types

from datetime import datetime

import jinja2
from babel import Locale
from bson.objectid import ObjectId

from flask import abort, request, session, current_app, g
from flask_babel import Babel
from flask_mongoengine import Pagination, MongoEngine
from flask.json import JSONEncoder, load
from flask_debugtoolbar import DebugToolbarExtension
from flask_wtf import CSRFProtect
from jinja2 import Undefined, evalcontextfilter
from markdown import Extension
from markdown.treeprocessors import Treeprocessor
from markupsafe import Markup
from mongoengine import Document, QuerySet
from speaklater import _LazyString
from werkzeug.routing import Rule
from werkzeug.urls import url_decode

toolbar = DebugToolbarExtension()


def new_show_toolbar(self):
    return 'debug' in request.args

toolbar._show_toolbar = types.MethodType(new_show_toolbar, toolbar)


class PrefixMiddleware(object):
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix
        if not self.prefix.startswith("/"):
            raise ValueError("Incorrect URL prefix value {prefix}".format(prefix=self.prefix))

    def __call__(self, environ, start_response):
        # Adds a prefix before all URLs consumed and produced
        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response('404', [('Content-Type', 'text/plain')])
            return ["This url does not belong to the app.".encode()]


class MethodRewriteMiddleware(object):
    """Rewrites POST with ending url /patch /put /delete into a proper PUT, PATCH, DELETE.
    Also has potential to add a prefix"""

    applied_methods = ['PUT', 'PATCH', 'DELETE']

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'POST':
            args = url_decode(environ['QUERY_STRING'])
            method = args.get('method', '').upper()
            if method and method in self.applied_methods:
                method = method.encode('ascii', 'replace')
                environ['REQUEST_METHOD'] = method
        return self.app(environ, start_response)


class FablrRule(Rule):
    allow_domains = False
    default_host = None
    re_sortkey = re.compile(r'[^/<]')
    match_order = None

    def bind(self, map, rebind=False):
        # if self.subdomain:  # Convert subdomain to full host rule
        # self.host = self.subdomain + '.' + self.default_host
        # Treat subdomains as full domain, as Flask-Classy only supports setting subdomain currently
        thehost = self.subdomain or None

        if thehost and not self.allow_domains:
            self.rule = "/host_" + thehost + "/" + self.rule.lstrip("/")
            self.subdomain = ''  # Hack, parent bind will check if None, '' will be read as having one
            self.host = ''
        else:
            self.host = thehost or self.default_host

        self.match_order = FablrRule.re_sortkey.sub('', self.rule)
        super(FablrRule, self).bind(map, rebind)

    # def match_compare_key(self):
    #     tup = super(FablrRule, self).match_compare_key()
    #     # TODO currently inactivated
    #     # For each level in path, we want fixed rules before variable rules, e.g. /worlds/<bc> before /<pub>/ab
    #     # From werkzeug
    #     # 1.  rules without any arguments come first for performance
    #     #     reasons only as we expect them to match faster and some
    #     #     common ones usually don't have any arguments (index pages etc.)
    #     # 2.  The more complex rules come first so the second argument is the
    #     #     negative length of the number of weights.
    #     # 3.  lastly we order by the actual weights.
    #     # tup = (self.match_order,) + tup
    #     #tup = (0,) + tup
    #     return tup


def db_config_string(app):
    # Clean to remove password
    return re.sub(r':([^/]+?)@', ':<REMOVED_PASSWORD>@', app.config['MONGODB_HOST'])


def is_db_empty(the_db):
    print(the_db.collection_names(False))


db = MongoEngine()


class MongoJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Document) or isinstance(o, QuerySet):
            return o.to_json()
        elif isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, Pagination):
            return {'page': o.page, 'per_page': o.per_page, 'pages': o.pages, 'total': o.total}
        if isinstance(o, _LazyString):  # i18n Babel uses lazy strings, need to be treated as string here
            return str(o)
        return JSONEncoder.default(self, o)


babel = Babel()
configured_locales = set()


def pick_locale():
    """
    Called by Flask Babel on each request to determine which locale to use, subsequently cached during request.

    - There are two types of available locales - the content and the interface.
    - No content locale means it can be assumed that there is no content to localize (only interface)
    - Content locales need to be set in g object before any translation happens, or you need to call refresh() on Babel to
      run this function again
    - User locale preference is either a single choice from URL or cookie, otherwise from HTTP request lang.
    - Never allow mismatch of interface and content locale.
    - If not match can be made, return 404 if the locale was specified in URL, otherwise fallback to default locale
    (consider always making locale part of URL to have no ambiguity)

    :return:
    """

    if not request or not g:
        return current_app.config.get('BABEL_DEFAULT_LOCALE', 'en')

    content_locales = g.get('content_locales', None)
    g.available_locales = {k: Locale.parse(k).language_name.capitalize() for k in
                           (configured_locales & content_locales if content_locales else configured_locales)}

    if 'locale' in request.args:
        preferred_locale = request.args['locale']
        if preferred_locale not in g.available_locales:
            # Hard abort as URL specified an unavailable locale
            abort(404,
                  u"Unsupported locale %s for this resource (supports %s)" % (preferred_locale, g.available_locales))
        else:
            session['locale'] = preferred_locale
    elif 'locale' in session:
        preferred_locale = session.get('locale')
    else:
        preferred_locale = request.accept_languages.best_match(list(g.available_locales.keys()))
    if preferred_locale not in g.available_locales:
        return None  # Babel will go to its default

    # print "Got lang %s, available_locale %s" % (preferred_locale, g.available_locales)
    return preferred_locale


csrf = CSRFProtect()


# Inspired by flask webpack but without any cruft
def init_assets(app):
    try:
        with app.open_resource(app.config.get('WEBPACK_MANIFEST_PATH'), 'r') as stats_json:
            app.assets = load(stats_json)
    except IOError as io:
        raise RuntimeError(
            "Asset management requires 'WEBPACK_MANIFEST_PATH' to be set and "
            "it must point to a valid json file. It was %s. %s" % (app.config.get('WEBPACK_MANIFEST_PATH'), io))


class GalleryList(Treeprocessor):
    def run(self, root):
        for ul in root.findall('ul'):
            if len(ul) and ul[0].text:
                h_text = ul[0].text.strip()
                if h_text in ['gallery-center', 'gallery-wide', 'gallery-card']:
                    ul.set('class', 'gallery %s' % h_text)
                    ul[0].set('class', 'hide')
                    for li in list(ul)[1:]:
                        li.set('class', 'gallery-item')
                        img = li.find('.//img')
                        if img is not None:
                            alt = img.get('alt', None)
                            if alt:
                                li.set('title', alt)
                                # a_el = etree.Element('a')
                                # a_el.set('href', '#')
                                # a_el.set('class', 'zoomable')
                                # a_el.extend(list(li))  # list(li) enumerates all children of li
                                # # for e in li:
                                # #     li.remove(e)
                                # li.append(a_el)
                                # imgs = list(ul.iterfind('.//img'))
                                # txts = list(ul.itertext())[1:]  # Skip first as it is the current node, e.g. ul
                                # # if there are same amount of images as text items, and the text is zero,
                                # we have only images in the list
                                # # however, they may be nested in other tags, e.g. a
                                # if ''.join(txts).strip() == '':  # All text nodes empty in the list


class GalleryList(Treeprocessor):
    def run(self, root):
        for ul in root.findall('ul'):
            if len(ul):
                imgs = list(ul.iterfind('.//img'))
                txts = list(ul.itertext())[1:]  # Skip first as it is the current node, e.g. ul
                if len(imgs) > 0 and ''.join(txts).strip() == '':
                    ul.set('class', 'gallery')


class AutolinkedImage(Extension):
    def extendMarkdown(self, md, md_globals):
        md.treeprocessors['gallery'] = GalleryList()


def build_md_filter(md_instance):
    @evalcontextfilter
    def markdown_filter(eval_ctx, stream):
        if not stream:
            return Markup('')
        elif eval_ctx.autoescape:
            return Markup(md_instance.convert(jinja2.escape(stream)))
        else:
            return Markup(md_instance.convert(stream))

    return markdown_filter


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        print('JINJA2: something was undefined!')  # TODO, should print correct log error
        return None


def currentyear(nada):
    return datetime.utcnow().strftime('%Y')


def dict_without(value, *args):
    return {k: value[k] for k in list(value.keys()) if k not in args}


def dict_with(value, **kwargs):
    z = value.copy()
    z.update(kwargs)
    return z
