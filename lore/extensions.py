import re
import types
from operator import attrgetter

from datetime import datetime

import jinja2
from babel import Locale
from bson.objectid import ObjectId
from io import StringIO

from flask import abort, request, session, current_app, g, render_template
from flask_babel import Babel
from flask_mongoengine import Pagination, MongoEngine
from flask.json import JSONEncoder, load
from flask_debugtoolbar import DebugToolbarExtension
from flask_debugtoolbar.panels.route_list import RouteListDebugPanel
from flask_wtf import CSRFProtect
from jinja2 import Undefined, evalcontextfilter
from markdown import Extension
from markdown.treeprocessors import Treeprocessor
from markupsafe import Markup
from mongoengine import Document, QuerySet
from speaklater import _LazyString
from werkzeug.routing import Rule, BaseConverter
from werkzeug.urls import url_decode

toolbar = DebugToolbarExtension()


class PatchedRouteListDebugPanel(RouteListDebugPanel):
    # Patches the Route List Panel to include a template that shows hosts
    def content(self):
        return render_template("includes/patched_route_list.html", routes=self.routes)


# Monkey patch to only show toolbar if in request args
def new_show_toolbar(self):
    return "debug" in request.args


toolbar._show_toolbar = types.MethodType(new_show_toolbar, toolbar)


class PrefixMiddleware(object):
    """
    Runs this Lore instance after a prefix in the URI, e.g. domain.com/prefix/<normal site>
    """

    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix
        if not self.prefix.startswith("/"):
            raise ValueError("Incorrect URL prefix value {prefix}".format(prefix=self.prefix))

    def __call__(self, environ, start_response):
        # Adds a prefix before all URLs consumed and produced
        if environ["PATH_INFO"].startswith(self.prefix):
            environ["PATH_INFO"] = environ["PATH_INFO"][len(self.prefix) :]
            environ["SCRIPT_NAME"] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response("404", [("Content-Type", "text/plain")])
            return ["This url does not belong to the app.".encode()]


class MethodRewriteMiddleware(object):
    """Rewrites POST with ending url /patch /put /delete into a proper PUT, PATCH, DELETE.
    Also has potential to add a prefix"""

    applied_methods = ["PUT", "PATCH", "DELETE"]

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ["REQUEST_METHOD"] == "POST":
            args = url_decode(environ["QUERY_STRING"])
            method = args.get("method", "").upper()
            try:
                # ensure UTF-8 not byte
                method = method.decode("utf-8")
            except AttributeError:
                pass
            if method and method in self.applied_methods:
                # method = method.encode('ascii', 'replace')
                environ["REQUEST_METHOD"] = method
        return self.app(environ, start_response)


# class HostConverter(BaseConverter):
#     # Root host is the host we serve Lore from, without a publisher. It exists in a local
#     # and a non-local context. Local is running on special port and a localhost or other non-qualified hostname.
#     # Non-local is the externally exposed domain
#     # lore:9000/ --> pub: None (e.g. lore.test) (matches assumed Docker name)
#     # localhost:5000/ddd -> pub: None
#     # lore.test:9000/ --> pub:
#     # (DEFAULT|localhost)(\.\w{2,})?(:\d+)
#
#     # Lore accepts any host when serving requests, all rules automatically get a prefix to catch hosts.
#     # The g.pub_host variable includes the parsed host. If g.pub_host is None, it means we are not on a publisher
#     #
#
#     # localhost:5000/host_abc --> pub: abc
#     # abc.dev --> pub: abc
#     # abc.se --> pub: abc
#     # xyz.abc.se --> pub: xyz.abc
#     # Match publisher.xxx:1234,
#
#     def __init__(self, url_map, default=None):
#         super(HostConverter, self).__init__(url_map)
#         self.default = default
#         host = '.+?' if not default else default
#         self.regex = f'{host}(?:\.\w+)?(?::\d+)?'
#
#     def to_python(self, value):
#         return value
#
#     def to_url(self, value):
#         return self.default if self.default else value


class NotAnyConverter(BaseConverter):
    """Matches if one of the items are not provided.  Items can either be Python
    identifiers or strings::
        Rule('/<not(about, help, imprint, class, "foo,bar"):page_name>')
    :param map: the :class:`Map`.
    :param items: this function accepts the possible items as positional
                  arguments.
    """

    def __init__(self, map, *items):
        BaseConverter.__init__(self, map)
        self.regex = f"(?!{'|'.join([re.escape(x) for x in items])}).+"


class LoreRule(Rule):
    allow_domains = False
    default_host = None
    re_sortkey = re.compile(r"[^/<]")
    match_order = None

    def bind(self, map, rebind=False):
        # For routes that do not come with specific subdomain, we should match localhost, lore and DEFAULT_SERVER
        # lore is used when we run in a Docker context, it's assumed the service is called lore. We should also
        # match any port for above
        # For routes with subdomain, those routes will decide what to do
        # We can also attach the prefix host_abc to match the host abc, which is used when running on localhost
        # However, for publisher_home, we are matching the root path /, and therefore we need to send to "homepage"
        # if we cannot find the publisher
        # if self.subdomain:  # Convert subdomain to full host rule
        # self.host = self.subdomain + '.' + self.default_host
        # Treat subdomains as full domain, as Flask-Classy only supports setting subdomain currently
        thehost = self.subdomain or self.host or None

        if thehost and not self.allow_domains:
            self.rule = "/host_" + thehost + "/" + self.rule.lstrip("/")
            self.subdomain = ""  # Hack, parent bind will check if None, '' will be read as having one
            self.host = ""
        else:
            self.host = thehost or "<pub_host>"
            # self.host = thehost or self.default_host

        self.match_order = LoreRule.re_sortkey.sub("", self.rule)
        # print(self.host + '|' + self.rule)
        super(LoreRule, self).bind(map, rebind)

    # def match_compare_key(self):
    #     tup = super(LoreRule, self).match_compare_key()
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
    return re.sub(r":([^/]+?)@", ":<REMOVED_PASSWORD>@", app.config["MONGODB_HOST"])


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
            return {"page": o.page, "per_page": o.per_page, "pages": o.pages, "total": o.total}
        if isinstance(o, _LazyString):  # i18n Babel uses lazy strings, need to be treated as string here
            return str(o)
        return JSONEncoder.default(self, o)


babel = Babel()

configured_locales = {}
configured_langs = {}
default_locale = None
lang_prefix_rule = ""
not_lang_prefix_rule = ""

predefined_lang_displays = {
    "en": {"display_in": "in English", "read_in": "Read in English", "available_in": "Available in English"},
    "sv": {"display_in": "på svenska", "read_in": "Läs på svenska", "available_in": "Tillgänglig på svenska"},
}


def setup_locales(app):
    global configured_locales
    global configured_langs
    global default_locale
    global lang_prefix_rule
    global not_lang_prefix_rule

    default_locale = Locale.parse(app.config.get("BABEL_DEFAULT_LOCALE", "en_US"))
    configured_locales = {k: Locale.parse(k) for k in app.config.get("BABEL_AVAILABLE_LOCALES")}
    configured_langs = {k.split("_")[0]: loc for k, loc in configured_locales.items()}
    for k, v in configured_langs.items():
        setattr(v, "phrases", predefined_lang_displays.get(k, predefined_lang_displays["en"]))
    lang_prefix_rule = "<any(" + ",".join(configured_langs.keys()) + "):lang>"
    not_lang_prefix_rule = "<not(" + ",".join(configured_langs.keys()) + "):"


def pick_locale():
    g.configured_locales = configured_locales
    g.configured_langs = configured_langs
    if request and g and "lang" in g:
        if g.lang in configured_langs:
            return configured_langs[g.lang]
    return None  # Makes babel choose it's default locale


# def pick_locale():
#     """
#     Called by Flask Babel on each request to determine which locale to use, subsequently cached during request.

#     - There are two types of available locales - the content and the interface.
#     - No content locale means it can be assumed that there is no content to localize (only interface)
#     - Content locales need to be set in g object before any translation happens, or you need to call refresh() on Babel to
#       run this function again
#     - User locale preference is either a single choice from URL or cookie, otherwise from HTTP request lang.
#     - Never allow mismatch of interface and content locale.
#     - If not match can be made, return 404 if the locale was specified in URL, otherwise fallback to default locale
#     (consider always making locale part of URL to have no ambiguity)

#     :return:
#     """

#     if not request or not g:
#         return current_app.config.get('BABEL_DEFAULT_LOCALE', 'en')

#     content_locales = g.get('content_locales', None)
#     g.available_locales = {k: Locale.parse(k).language_name.capitalize() for k in
#                            (configured_locales & content_locales if content_locales else configured_locales)}

#     if 'locale' in request.args:
#         preferred_locale = request.args['locale']
#         if preferred_locale not in g.available_locales:
#             # Hard abort as URL specified an unavailable locale
#             request.babel_locale = babel.default_locale  # Need to set this as the exception will terminate the locale flow early
#             abort(404,
#                   u"Unsupported locale %s for this resource (supports %s)" % (preferred_locale, g.available_locales))
#         else:
#             session['locale'] = preferred_locale
#     elif 'locale' in session:
#         preferred_locale = session.get('locale')
#     else:
#         preferred_locale = request.accept_languages.best_match(list(g.available_locales.keys()))
#     if preferred_locale not in g.available_locales:
#         return None  # Babel will go to its default

#     # print "Got lang %s, available_locale %s" % (preferred_locale, g.available_locales)
#     return preferred_locale


csrf = CSRFProtect()


# Inspired by flask webpack but without any cruft
def init_assets(app):
    try:
        with app.open_resource(app.config.get("WEBPACK_MANIFEST_PATH"), "r") as stats_json:
            app.assets = load(stats_json)
    except IOError as io:
        raise RuntimeError(
            "Asset management requires 'WEBPACK_MANIFEST_PATH' to be set and "
            "it must point to a valid json file. It was %s. %s" % (app.config.get("WEBPACK_MANIFEST_PATH"), io)
        )


class GalleryList(Treeprocessor):
    def run(self, root):
        for ul in root.findall("ul"):
            if len(ul) and ul[0].text:
                h_text = ul[0].text.strip()
                if h_text in ["gallery-center", "gallery-wide", "gallery-card"]:
                    ul.set("class", "gallery %s" % h_text)
                    ul[0].set("class", "hide")
                    for li in list(ul)[1:]:
                        li.set("class", "gallery-item")
                        img = li.find(".//img")
                        if img is not None:
                            alt = img.get("alt", None)
                            if alt:
                                li.set("title", alt)
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


# Simpler version that only looks for lists of images
# class GalleryList(Treeprocessor):
#     def run(self, root):
#         for ul in root.findall('ul'):
#             if len(ul):
#                 imgs = list(ul.iterfind('.//img'))
#                 txts = list(ul.itertext())[1:]  # Skip first as it is the current node, e.g. ul
#                 if len(imgs) > 0 and ''.join(txts).strip() == '':
#                     ul.set('class', 'gallery')


class AutolinkedImage(Extension):
    def extendMarkdown(self, md, md_globals):
        md.treeprocessors["gallery"] = GalleryList()


# Hack to support removing markdown from text
def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


def build_md_filter(md_instance):
    @evalcontextfilter
    def markdown_filter(eval_ctx, stream):
        if not stream:
            return Markup("")
        elif eval_ctx.autoescape:
            return Markup(md_instance.convert(jinja2.escape(stream)))
        else:
            return Markup(md_instance.convert(stream))

    return markdown_filter


def enhance_jinja_loader(app):
    plugin_loader = jinja2.FileSystemLoader(["plugins"])
    plugins = [p.split("/")[0] for p in plugin_loader.list_templates() if p.endswith("index.html")]
    # app.logger.debug("Loaded templates: %s" % plugins)
    app.plugins = plugins
    return jinja2.ChoiceLoader([app.jinja_loader, plugin_loader])


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        current_app.logger.warning(f"JINJA2: undefined in template {request.url}!")
        return None


# Jinja Filters


def currentyear(nada):
    return datetime.utcnow()
    # return datetime.utcnow().strftime('%Y')


def dict_without(value, *args):
    return {k: value[k] for k in list(value.keys()) if k not in args}


def dict_with(value, **kwargs):
    z = value.copy()
    z.update(kwargs)
    return z


def first_p_length(string):
    return len(string.strip().splitlines()[0]) if string else 0


def lookup(s, dct, default=None):
    return dct.get(s, s or default)


def safe_id(s):
    # Replaces character not safe for HTML ID:s https://www.w3.org/TR/html4/types.html#type-id
    s = re.sub(r"^[^A-Za-z]", "", s)
    s = re.sub(r"[^A-Za-z0-9-_:]+", "-", s)
    return s


def filter_by_any_scopes(items, *scopes_to_match):
    """Filters a list of items based on if their scopes match any of the provided scopes.
    An item matches if it has no scope (valid for any scope) or if the intersection
    of item's scopes and scopes to match is at least one (e.g at least one scope in both).

    Args:
        items ([type]): [description]

    Returns:
        [type]: [description]
    """
    scopes_to_match = set(scopes_to_match)
    return [i for i in items if not i.scopes or set(map(attrgetter("pk"), i.scopes)) & scopes_to_match]


def filter_by_all_scopes(items, *scopes_to_match):
    """Filters a list of items based on if their scopes match all the provided scopes.
    An item matches if it has no scope (valid for any scope) or if scopes to match is
    a subset of the items scopes.

    Args:
        items ([type]): [description]

    Returns:
        [type]: [description]
    """
    scopes_to_match = set(scopes_to_match)
    return [i for i in items if not i.scopes or set(map(attrgetter("pk"), i.scopes)) >= scopes_to_match]
