"""
  lore.app
  ~~~~~~~~~~~~~~~~

  Main Lore application class, that initializes the Flask application,
  it's blueprints, plugins and template filters.

  :copyright: (c) 2014 by Helmgast AB
"""

import datetime
import os
import re
from logging import DEBUG, INFO, Formatter, StreamHandler, getLogger
from time import time

from flask import (
    Flask,
    flash,
    g,
    got_request_exception,
    logging,
    redirect,
    render_template,
    request,
    current_app,
    url_for,
    send_from_directory,
)
from flask.config import Config
from markdown import Markdown
from mongoengine.connection import ConnectionFailure
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.routing import Map
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration


def create_app(**kwargs):

    # Creates new flask instance
    the_app = Flask("lore", static_folder="../static")

    config_string = "config from:"
    from . import default_config

    the_app.config.from_object(default_config.Config)  # Default config that applies to all deployments
    the_app.config.from_object(default_config.SecretConfig)  # Add dummy secrets

    # 1. Load specific configuration in the following order, so that last applies local config.py
    fileconfig = Config(the_app.root_path)
    fileconfig.from_pyfile("../config.py", silent=True)
    the_app.config.update(fileconfig)

    # 2. Environment variables (only if exist in default)
    # TODO there could be name collision with env variables, and this may be unsafe
    envconfig = Config(the_app.root_path)
    for k in the_app.config.keys():
        env_k = "LORE_%s" % k
        if env_k in os.environ:
            env_v = os.environ[env_k]
            if str(env_v).lower() in ["true", "false"]:
                env_v = str(env_v).lower() == "true"
            envconfig[k] = env_v
    the_app.config.update(envconfig)

    # 3. Arguments from run function (only if exist in default)
    argconfig = Config(the_app.root_path)
    for k in kwargs.keys():
        if k in the_app.config:
            argconfig[k] = kwargs[k]
    the_app.config.update(argconfig)

    config_msg = ""
    # 4. Check if running in production or not
    if the_app.config["PRODUCTION"]:
        # Make sure we don't debug in production
        the_app.debug = False
        # Show a sanitized config output in justified columns
        width = max(map(len, (argconfig.keys() | envconfig.keys() | fileconfig.keys() | {""})))

        def sanitize(k, v):
            return "***" if getattr(default_config.SecretConfig, k, None) else v

        for k in the_app.config:
            if k in argconfig:
                config_msg += f"{k.ljust(width)}(args) = {sanitize(k, argconfig[k])}\n"
            elif k in envconfig:
                config_msg += f"{k.ljust(width)}(env)  = {sanitize(k, envconfig[k])}\n"
            elif k in fileconfig:
                config_msg += f"{k.ljust(width)}(file) = {sanitize(k, fileconfig[k])}\n"

    # the_app.config['PROPAGATE_EXCEPTIONS'] = the_app.debug
    configure_logging(the_app)
    if not the_app.testing:
        the_app.logger.info(
            "Lore (%s) started. Mode: %s%s:\n%s"
            % (
                the_app.config.get("VERSION", None),
                "Prod" if the_app.config["PRODUCTION"] else "Dev",
                " (Debug)" if the_app.debug else "",
                config_msg,
            )
        )

    # Configure all extensions
    configure_extensions(the_app)

    # Configure all blueprints
    configure_blueprints(the_app)

    configure_hooks(the_app)

    return the_app


def configure_logging(app):
    # Custom logging that always goes to stderr
    logger = getLogger(app.logger_name)

    class RequestFormatter(logging.Formatter):
        def format(self, record):
            record.url = request.url if request else ""
            return super().format(record)

    handler = StreamHandler(logging._proxy_stream)
    handler.setFormatter(
        RequestFormatter("[%(asctime)s %(levelname)s in %(module)s:%(lineno)d] %(message)s (%(url)s)")
    )
    logger.addHandler(handler)
    logger.setLevel(DEBUG if app.debug else INFO)
    app._logger = logger  # Replace the otherwise auto-configured logger
    sentry_dsn = app.config["SENTRY_DSN"]

    if app.config["PRODUCTION"]:
        if sentry_dsn and sentry_dsn != "SECRET":  # SECRET is default, non-set state
            sentry_sdk.init(
                dsn=sentry_dsn, integrations=[FlaskIntegration(transaction_style="url")], send_default_pii=True
            )
        else:
            app.logger.warning("Running without Sentry error monitoring; no SENTRY_DSN in config")

    # app.logger.debug("Debug")
    # app.logger.info("Info")
    # app.logger.warning("Warning")
    # app.logger.error("Error")
    # app.logger.info("Info")


def configure_extensions(app):
    from . import extensions

    # URL and routing
    prefix = app.config.get("URL_PREFIX", "")
    if prefix:
        app.wsgi_app = extensions.PrefixMiddleware(app.wsgi_app, prefix)
    # Fixes IP address etc assuming we run behind proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    # Rewrites POSTs with specific methods into the real method, to allow HTML forms to send PUT, DELETE, etc
    app.wsgi_app = extensions.MethodRewriteMiddleware(app.wsgi_app)
    if not app.config["PRODUCTION"]:
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # Don't cache files in development mode

    app.url_rule_class = extensions.LoreRule

    # default_hosts = ['localhost:5000', app.config['DEFAULT_HOST']]
    # t = '","'.join(default_hosts)
    # app.default_host = f'<any("{t}"):pub_host>'
    app.default_host = app.config["DEFAULT_HOST"]
    app.url_rule_class.allow_domains = True
    app.url_rule_class.default_host = app.config["DEFAULT_HOST"]
    app.url_map = Map(host_matching=True)
    app.url_map.converters["not"] = extensions.NotAnyConverter

    # Re-add the static rule

    app.add_url_rule(
        app.static_url_path + "/<path:filename>",
        endpoint="static",
        view_func=app.send_static_file,
        # host=app.default_host,
    )
    app.logger.info(
        "Doing host matching and default host is {host}{prefix}".format(host=app.default_host, prefix=prefix or "")
    )

    # Special static function that serves from plugin/ instead of static/
    def send_plugin_file(filename):
        return send_from_directory("../plugins", filename, cache_timeout=current_app.get_send_file_max_age(filename))

    app.add_url_rule(
        "/plugins/<path:filename>",
        endpoint="plugins",
        view_func=send_plugin_file,
        # host=app.default_host
    )

    # Debug toolbar, will stop if DEBUG_TB_ENABLED = False or if not else if DEBUG=False
    extensions.toolbar.init_app(app)

    # TODO this is a hack to allow authentication via source db admin,
    # will likely break if connection is recreated later
    # mongocfg =   app.config['MONGODB_SETTINGS']
    # db.connection[mongocfg['DB']].authenticate(mongocfg['USERNAME'], mongocfg['PASSWORD'], source="admin")

    # Internationalization
    extensions.babel.init_app(app)  # Automatically adds the extension to Jinja as well

    # Register callback that tells which language to serve
    try:
        extensions.babel.localeselector(extensions.pick_locale)
    except AssertionError as ae:
        app.logger.warning(ae)

    extensions.setup_locales(app)
    if app.config.get("BABEL_DEFAULT_LOCALE") not in extensions.configured_locales:
        raise ValueError("Incorrectly configured locales")

    # Secure forms
    extensions.csrf.init_app(app)

    # Read static file manifest from webpack
    extensions.init_assets(app)

    # app.md = FlaskMarkdown(app, extensions=['attr_list'])
    # app.md.register_extension(extensions.AutolinkedImage)

    app.md = Markdown(
        extensions=[
            "markdown.extensions.attr_list",
            "markdown.extensions.smarty",
            "markdown.extensions.tables",
            extensions.AutolinkedImage(),
        ]
    )
    # A small hack to let us output "unmarkdownified" text.
    Markdown.output_formats["plain"] = extensions.unmark_element
    app.md_plain = Markdown(output_format="plain")
    app.md_plain.stripTopLevelTags = False

    app.jinja_env.filters["markdown"] = extensions.build_md_filter(app.md)
    app.jinja_env.filters["md2plain"] = extensions.build_md_filter(app.md_plain)
    app.jinja_env.filters["dict_with"] = extensions.dict_with
    app.jinja_env.filters["dict_without"] = extensions.dict_without
    app.jinja_env.filters["currentyear"] = extensions.currentyear
    app.jinja_env.filters["first_p_length"] = extensions.first_p_length
    app.jinja_env.filters["lookup"] = extensions.lookup
    app.jinja_env.filters["safe_id"] = extensions.safe_id
    app.jinja_env.filters["filter_by_all_scopes"] = extensions.filter_by_all_scopes
    app.jinja_env.filters["filter_by_any_scopes"] = extensions.filter_by_any_scopes
    app.jinja_env.add_extension("jinja2.ext.do")  # "do" command in jinja to run code
    app.jinja_loader = extensions.enhance_jinja_loader(app)
    app.json_encoder = extensions.MongoJSONEncoder
    if not app.debug:
        # Silence undefined errors in templates if not debug
        app.jinja_env.undefined = extensions.SilentUndefined
    # app.jinja_options = ImmutableDict({'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_']})


# Dummy function that returns what it was passed
def identity(ob):
    return ob


def configure_blueprints(app):
    with app.app_context():
        from .api.auth import auth_app
        from .extensions import lang_prefix_rule

        app.register_blueprint(auth_app, url_prefix="/auth")
        app.access_policy = {}

        from .api.world import world_app as world
        from flask_babel import lazy_gettext as _

        world.plugin_choices = [("None", _("None"))] + [(v, v) for v in app.plugins]
        from .api.asset import asset_app as asset_app
        from .api.social import social
        from .api.generator import generator
        from .api.admin import admin
        from .api.shop import shop_app as shop
        from .api.mailer import mail_app as mail

        app.register_blueprint(world, url_defaults={"lang": "sv"})
        app.register_blueprint(
            world, url_prefix=f"/{lang_prefix_rule}"
        )  # No url_prefix as we build it up as /<world>/<article>

        app.register_blueprint(generator, url_prefix="/generator")
        app.register_blueprint(admin, url_prefix="/admin")

        app.register_blueprint(social, url_prefix=f"/social", url_defaults={"lang": "sv"})
        app.register_blueprint(social, url_prefix=f"/{lang_prefix_rule}/social")

        app.register_blueprint(shop, url_prefix=f"/shop", url_defaults={"lang": "sv"})
        app.register_blueprint(shop, url_prefix=f"/{lang_prefix_rule}/shop")

        app.register_blueprint(asset_app, url_prefix="/assets")

        app.register_blueprint(mail, url_prefix=f"/mail", url_defaults={"lang": "sv"})
        app.register_blueprint(mail, url_prefix=f"/{lang_prefix_rule}/mail")

        from sparkpost import SparkPost

        mail.sparkpost_client = SparkPost(app.config["SPARKPOST_API_KEY"])

    return auth_app


def configure_hooks(app):

    from flask_babel import get_locale
    from lore.api.resource import mark_time_since_request

    app.add_template_global(get_locale)

    @app.before_request
    def start_time():
        g.start = time()

    @app.before_first_request
    def start_db():
        # Lazily start the database connection at first request.
        from lore import extensions
        from flask_mongoengine.connection import get_connection_settings, _connect

        # TODO A hack, that bypasses the config sanitization of Flask-Mongoengine so we can add custom Mongo config
        # https://github.com/MongoEngine/flask-mongoengine/issues/327
        extensions.db.init_app(app, config={"MONGODB_SETTINGS": []})
        db_settings = get_connection_settings(app.config)
        db_settings["serverSelectionTimeoutMS"] = 5000  # Shortened from 30000 default
        try:
            app.extensions["mongoengine"][extensions.db] = {"app": app, "conn": _connect(db_settings)}
        except ConnectionFailure:
            pass  # We need to leave this method without an exception, as the request finishes, the exception will raise again

    # Fetches pub_host from raw url (e.g. subdomain) and removes it from view args
    @app.url_value_preprocessor
    def get_global_url_vars(endpoint, values):
        ph = values.pop("pub_host", None) if values else None
        if not ph:
            ph = request.host
        if not app.config["PRODUCTION"]:
            ph = re.sub(r"\.test$", "", ph)
        g.pub_host = ph
        lang = values.pop("lang", None) if values else None
        g.lang = lang

    # Adds pub_host when building URL if it was not provided and expected by the route
    @app.url_defaults
    def set_global_url_vars(endpoint, values):
        if app.url_map.is_endpoint_expecting(endpoint, "pub_host"):
            if app.config["PRODUCTION"]:
                values.setdefault("pub_host", g.pub_host)
            elif "pub_host" not in values:
                # No pub_host given so we will default to the current pub_host plus test
                values["pub_host"] = g.pub_host + ".test"
            elif not values.get("_external", False):
                # pub_host was given, and _external is False, so we can add .test
                # (if external is True we assume the URL is for actual use and must resolve outside dev )
                values["pub_host"] = values["pub_host"] + ".test"
        if app.url_map.is_endpoint_expecting(endpoint, "lang") and "lang" in g:
            values.setdefault("lang", g.lang)
        # mark_time_since_request(f"URL defaults for {endpoint}")

    @app.context_processor
    def inject_access():
        return dict(access_policy=app.access_policy, debug=app.debug, assets=app.assets, plugins=app.plugins)

    from lore.model.misc import current_url, in_current_args, slugify, delta_date
    from lore.api.auth import auth0_url
    from lore.model.asset import cloudinary_url
    from sentry_sdk import last_event_id, capture_exception

    app.add_template_global(cloudinary_url)
    app.add_template_global(auth0_url)
    app.add_template_global(current_url)
    app.add_template_global(in_current_args)
    app.add_template_global(slugify)
    app.add_template_global(delta_date)
    app.add_template_global(datetime.datetime.utcnow, name="now")

    @app.errorhandler(401)  # Unauthorized or unauthenticated, e.g. not logged in
    def unauthorized(err):
        # capture_exception(err)  # Explicitly capture exception to Sentry
        return (
            render_template(
                "error/401.html", root_template="_root.html", publisher_theme=g.get("publisher_theme", None)
            ),
            401,
        )

    @app.errorhandler(403)
    def forbidden(err):
        capture_exception(err)  # Explicitly capture exception to Sentry
        return (
            render_template(
                "error/403.html",
                root_template="_root.html",
                error=err,
                publisher_theme=g.get("publisher_theme", None),
                sentry_event_id=last_event_id(),
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(err):
        # if app.debug:
        #     # We want to show debug toolbar if we get 404, but needs to return an HTML page with status 200 for it
        #     # to activate
        #     return render_template("error/404.html", root_template='_root.html', error=f"{request.path} not found at host {request.host}"), 200
        return (
            render_template(
                "error/404.html",
                root_template="_root.html",
                error=err.description or f"{request.path} not found at host {request.host}",
                publisher_theme=g.get("publisher_theme", None),
            ),
            404,
        )

    @app.errorhandler(ConnectionFailure)
    def db_error(err):
        app.logger.error("Database Connection Failure: {err}".format(err=err))
        return render_template("error/nodb.html", root_template="_root.html"), 500

    from lore.api.resource import ResourceError, get_root_template

    @app.errorhandler(ResourceError)
    def resource_error(err):
        # if request.args.has_key('debug') and current_app.debug:
        #     raise # send onward if we are debugging

        if err.status_code == 400:  # bad request
            if err.template:
                flash(err.message, "warning")
                err.template_vars["root_template"] = get_root_template(request.args.get("out", None))
                return render_template(err.template, **err.template_vars), err.status_code
        raise err  # re-raise if we don't have a template

    @app.errorhandler(500)
    def server_error(err):
        return (
            render_template("error/500.html", err=err, root_template="_root.html", sentry_event_id=last_event_id()),
            500,
        )


# @current_app.template_filter('dictreplace')
# def dictreplace(s, d):
#   if d and len(d) > 0:
#     parts = s.split("__")
#     # Looking for variables __key__ in s.
#     # Splitting on __ makes every 2nd part a key, starting with index 1 (not 0)
#     for i in range(1, len(parts), 2):
#       parts[i] = d[parts[i]]  # Replace with dict content
#     return ''.join(parts)
#   return s
