"""
  lore.app
  ~~~~~~~~~~~~~~~~

  Main Lore application class, that initializes the Flask application,
  it's blueprints, plugins and template filters.

  :copyright: (c) 2014 by Helmgast AB
"""
from __future__ import absolute_import

import datetime
import os
from builtins import str
from logging import DEBUG, INFO, Formatter, StreamHandler, getLogger

import rollbar
from flask import (Flask, flash, g, got_request_exception, logging, redirect,
                   render_template, request, current_app, url_for, send_from_directory)
from flask.config import Config
from markdown import Markdown
from pymongo.errors import ConnectionFailure
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.routing import Map


def create_app(**kwargs):

    # Creates new flask instance
    the_app = Flask('lore', static_folder='../static')
    
    config_string = "config from:"
    from . import default_config
    the_app.config.from_object(default_config.Config)  # Default config that applies to all deployments
    the_app.config.from_object(default_config.SecretConfig)  # Add dummy secrets
        
    # Load specific configuration in the following order, so that last applies
    # local config.py
    fileconfig = Config(the_app.root_path)
    fileconfig.from_pyfile('../config.py', silent=True)
    the_app.config.update(fileconfig)

    # 2. Environment variables (only if exist in default)
    # TODO there could be name collision with env variables, and this may be unsafe
    envconfig = Config(the_app.root_path)
    for k in the_app.config.keys():
        env_k = 'LORE_%s' % k
        if env_k in os.environ:
            env_v = os.environ[env_k]
            if str(env_v).lower() in ['true', 'false']:
                env_v = str(env_v).lower() == 'true'
            envconfig[k] = env_v
    the_app.config.update(envconfig)

    # 3. Arguments to run (only if exist in default)
    argconfig = Config(the_app.root_path)
    for k in kwargs.keys():
        if k in the_app.config:
            argconfig[k] = kwargs[k]
    the_app.config.update(argconfig)

    config_msg = ""
    if not the_app.debug:
        # For tight columns, get longest key name we need to print
        width = max(map(len, (argconfig.keys() | envconfig.keys() | fileconfig.keys() | {''})))

        def secretize(k,v):
            return "***" if not the_app.debug and getattr(default_config.SecretConfig, k, None) else v
        for k in the_app.config:
            if k in argconfig:
                config_msg += f"{k.ljust(width)}(args) = {secretize(k, argconfig[k])}\n"
            elif k in envconfig:
                config_msg += f"{k.ljust(width)}(env)  = {secretize(k, envconfig[k])}\n"
            elif k in fileconfig:
                config_msg += f"{k.ljust(width)}(file) = {secretize(k, fileconfig[k])}\n"

    # the_app.config['PROPAGATE_EXCEPTIONS'] = the_app.debug
    # raise ValueError("Test config")
    configure_logging(the_app)
    if not the_app.testing:
        the_app.logger.info("Flask '%s' (%s) created in %s-mode:\n%s"
                            % (the_app.name, the_app.config.get('VERSION', None),
                               "Debug" if the_app.debug else "Prod", config_msg))

    # Configure all extensions
    configure_extensions(the_app)

    # Configure all blueprints
    configure_blueprints(the_app)

    configure_hooks(the_app)

    return the_app


def my_report_exception(app, exception):
    # Modified from rollbar.contrib.flask to automatically insert user data
    if g.user:
        person = {'id': g.user.id, 'email': g.user.email}
    else:
        person = {'id': request.remote_addr if request else 'non-request'}
    rollbar.report_exc_info(request=request, payload_data={'person': person})


def configure_logging(app):
    # Custom logging that always goes to stderr
    logger = getLogger(app.logger_name)

    class RequestFormatter(logging.Formatter):
        def format(self, record):
            record.url = request.url if request else ''
            return super().format(record)

    handler = StreamHandler(logging._proxy_stream)
    handler.setFormatter(RequestFormatter('[%(levelname)s in %(module)s:%(lineno)d (%(url)s)] %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(DEBUG if app.debug else INFO)
    app._logger = logger  # Replace the otherwise auto-configured logger

    rollbar_token = app.config['ROLLBAR_TOKEN']
    if not app.debug:
        if rollbar_token != 'SECRET':  # SECRET is default, non-set state
            rollbar.init(
                rollbar_token,
                # environment name
                'lore',
                # server root directory, makes tracebacks prettier
                root=os.path.dirname(os.path.realpath(__file__)),
                # flask already sets up logging
                allow_logging_basic_config=False)

            # send exceptions from `app` to rollbar, using flask's signal system.
            # got_request_exception.connect(rollbar.contrib.flask.report_exception, app)
            got_request_exception.connect(my_report_exception, app)
            rollbar.report_message("Initiated rollbar on %s" % app.config.get('VERSION', None), 'info')
        else:
            app.logger.warning("Running without Rollbar error monitoring; no ROLLBAR_TOKEN in config")

            # app.logger.debug("Debug")
            # app.logger.info("Info")
            # app.logger.warning("Warning")
            # app.logger.error("Error")
            # app.logger.info("Info")


def configure_extensions(app):
    from . import extensions
    
    # URL and routing
    prefix = app.config.get('URL_PREFIX', '')
    if prefix:
        app.wsgi_app = extensions.PrefixMiddleware(app.wsgi_app, prefix)
    # Fixes IP address etc if running behind proxy
    app.wsgi_app = ProxyFix(app.wsgi_app)
    # Rewrites POSTs with specific methods into the real method, to allow HTML forms to send PUT, DELETE, etc
    app.wsgi_app = extensions.MethodRewriteMiddleware(app.wsgi_app)

    app.url_rule_class = extensions.LoreRule

    # default_hosts = ['localhost:5000', app.config['DEFAULT_HOST']]
    # t = '","'.join(default_hosts)
    # app.default_host = f'<any("{t}"):pub_host>'
    app.default_host = app.config['DEFAULT_HOST']
    app.url_rule_class.allow_domains = True
    app.url_rule_class.default_host = app.config['DEFAULT_HOST']
    app.url_map = Map(host_matching=True)
    # Re-add the static rule
    app.add_url_rule(app.static_url_path + '/<path:filename>', endpoint='static',
                        view_func=app.send_static_file, host=app.default_host)
    app.logger.info('Doing host matching and default host is {host}{prefix}'.format(
        host=app.default_host, prefix=prefix or ''))

    # Special static function that serves from plugin/ instead of static/
    def send_plugin_file(filename):
        return send_from_directory('../plugins', filename, cache_timeout=current_app.get_send_file_max_age(filename))

    app.add_url_rule('/plugins/<path:filename>', endpoint='plugins', view_func=send_plugin_file, host=app.default_host)

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

    extensions.configured_locales = set(app.config.get('BABEL_AVAILABLE_LOCALES'))
    if not extensions.configured_locales or app.config.get('BABEL_DEFAULT_LOCALE') not in extensions.configured_locales:
        app.logger.warning('Incorrectly configured: BABEL_DEFAULT_LOCALE %s not in BABEL_AVAILABLE_LOCALES %s' %
                           app.config.get('BABEL_DEFAULT_LOCALE'), app.config.get('BABEL_AVAILABLE_LOCALES'))
        extensions.configured_locales = set(app.config.get('BABEL_DEFAULT_LOCALE'))

    # Secure forms
    extensions.csrf.init_app(app)

    # Read static file manifest from webpack
    extensions.init_assets(app)

    # app.md = FlaskMarkdown(app, extensions=['attr_list'])
    # app.md.register_extension(extensions.AutolinkedImage)

    app.md = Markdown(extensions=['markdown.extensions.attr_list',
                                  'markdown.extensions.smarty',
                                  'markdown.extensions.tables',
                                  extensions.AutolinkedImage()])

    app.jinja_env.filters['markdown'] = extensions.build_md_filter(app.md)
    app.jinja_env.filters['dict_with'] = extensions.dict_with
    app.jinja_env.filters['dict_without'] = extensions.dict_without
    app.jinja_env.filters['currentyear'] = extensions.currentyear
    app.jinja_env.add_extension('jinja2.ext.do')  # "do" command in jinja to run code
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
        app.register_blueprint(auth_app, url_prefix='/auth')
        app.access_policy = {}

        from .api.world import world_app as world
        from .api.asset import asset_app as asset_app
        from .api.social import social
        from .api.generator import generator
        from .api.admin import admin
        from .api.shop import shop_app as shop
        from .api.mailer import mail_app as mail

        app.register_blueprint(world)  # No url_prefix as we build it up as /<world>/<article>
        app.register_blueprint(generator, url_prefix='/generator')
        app.register_blueprint(admin, url_prefix='/admin')
        app.register_blueprint(social, url_prefix='/social')
        app.register_blueprint(shop, url_prefix='/shop')
        app.register_blueprint(asset_app, url_prefix='/assets')
        app.register_blueprint(mail, url_prefix='/mail')
        from sparkpost import SparkPost
        mail.sparkpost_client = SparkPost(app.config['SPARKPOST_API_KEY'])

    return auth_app


def configure_hooks(app):

    from flask_babel import get_locale
    app.add_template_global(get_locale)

    # @app.before_request
    # def load_locale():
    #     g.available_locales = available_locales_tuple

    @app.before_first_request
    def start_db():
        # Lazily start the database connection at first request.
        from lore import extensions
        from flask_mongoengine.connection import get_connection_settings, _connect
        # TODO A hack, that bypasses the config sanitization of Flask-Mongoengine so we can add custom Mongo config
        # https://github.com/MongoEngine/flask-mongoengine/issues/327
        extensions.db.init_app(app, config={'MONGODB_SETTINGS':[]})
        db_settings = get_connection_settings(app.config)
        db_settings['serverSelectionTimeoutMS'] = 5000  # Shortened from 30000 default
        app.extensions['mongoengine'][extensions.db] = {'app':app, 'conn': _connect(db_settings)}
        

    # Fetches pub_host from raw url (e.g. subdomain) and removes it from view args
    @app.url_value_preprocessor
    def get_pub_host(endpoint, values):
        ph = values.pop('pub_host', None) if values else None
        if not ph:
            ph = request.host
        g.pub_host = ph

    # Adds pub_host when building URL if it was not provided and expected by the route
    @app.url_defaults
    def set_pub_host(endpoint, values):
        if app.url_map.is_endpoint_expecting(endpoint, 'pub_host'):
            values.setdefault('pub_host', g.pub_host)

    @app.context_processor
    def inject_access():
        return dict(access_policy=app.access_policy, debug=app.debug, assets=app.assets, plugins=app.plugins)

    from lore.model.misc import current_url, in_current_args, slugify, delta_date
    from lore.api.auth import auth0_url
    app.add_template_global(auth0_url)
    app.add_template_global(current_url)
    app.add_template_global(in_current_args)
    app.add_template_global(slugify)
    app.add_template_global(delta_date)
    app.add_template_global(datetime.datetime.utcnow, name="now")

    @app.errorhandler(401)  # Unauthorized, e.g. not logged in
    def unauthorized(e):
        if request.method == 'GET':  # Only do sso on GET requests
            return redirect(url_for('auth.sso', next=request.url))
        else:
            app.logger.warning(
                "Could not handle 401 Unauthorized for {url} as it was not a GET".format(url=request.url))
            return e, 401

    @app.errorhandler(404)
    def not_found(err):
        if app.debug:
            # We want to show debug toolbar if we get 404, but needs to return an HTML page with status 200 for it
            # to activate
            return render_template("error/404.html", error=f"{request.path} not found at host {request.host}"), 200
        return f"{request.path} not found at host {request.host}", 404
        # return render_template('error/404.html', root_template='_page.html'), 404

    @app.errorhandler(ConnectionFailure)
    def db_error(err):
        app.logger.error("Database Connection Failure: {err}".format(err=err))
        return render_template('error/nodb.html', root_template='_page.html'), 500

    from lore.api.resource import ResourceError, get_root_template

    @app.errorhandler(ResourceError)
    def resource_error(err):
        # if request.args.has_key('debug') and current_app.debug:
        #     raise # send onward if we are debugging

        if err.status_code == 400:  # bad request
            if err.template:
                flash(err.message, 'warning')
                err.template_vars['root_template'] = get_root_template(request.args.get('out', None))
                return render_template(err.template, **err.template_vars), err.status_code
        raise err  # re-raise if we don't have a template

    # for rule in sorted(app.url_map.iter_rules(), key=lambda rule: rule.match_compare_key()):
    #     print(rule.__repr__(), rule.subdomain, rule.match_compare_key())

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