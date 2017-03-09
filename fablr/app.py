"""
  fablr.app
  ~~~~~~~~~~~~~~~~

  Main Fablr application class, that initializes the Flask application,
  it's blueprints, plugins and template filters.

  :copyright: (c) 2014 by Helmgast AB
"""

import os
import urllib

import sys

import rollbar
from flask import Flask, render_template, request, url_for, flash, g
from flask import got_request_exception
from flaskext.markdown import Markdown
from pymongo.errors import ConnectionFailure
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.routing import Map

from fablr.controller.resource import ResourceError, get_root_template


def create_app(no_init=False, **kwargs):
    # Creates new flask instance, also keeps static at
    the_app = Flask('fablr', static_folder='../static')
    config_string = "config from:"
    import default_config
    the_app.config.from_object(default_config.Config)  # Default config that applies to all deployments
    the_app.config.from_object(default_config.SecretConfig)  # Add dummy secrets
    try:  # Instead of silent=True, use try/except to be able to write config_string only if loaded
        the_app.config.from_pyfile('../config.py', silent=False)  # Now override with custom settings if exist
        config_string += " file config.py, "
    except IOError:
        pass

    # Override defaults with any environment variables, as long as they are defined in default.
    # TODO there could be name collision with env variables, and this may be unsafe
    env_config = []
    for k in the_app.config.iterkeys():
        env_k = 'FABLR_%s' % k
        if env_k in os.environ:
            env_v = os.environ[env_k]
            if str(env_v).lower() in ['true', 'false']:
                env_v = str(env_v).lower() == 'true'
            the_app.config[k] = env_v
            env_config.append(k)
    if env_config:
        config_string += " env (%s), " % ','.join(env_config)

    the_app.config.update(kwargs)  # add any overrides from startup command
    the_app.config['PROPAGATE_EXCEPTIONS'] = the_app.debug


    # If in production, make sure we don't have any dummy secrets
    if not the_app.debug:
        for key in dir(default_config.SecretConfig):
            if key.isupper():
                if the_app.config[key] == 'SECRET':
                    raise ValueError(
                        "Secret key %s given dummy value in production - ensure it's overriden. "
                        "Config method was: %s" %
                        (key, config_string))

    configure_logging(the_app)

    if not the_app.testing:
        the_app.logger.info("Flask '%s' (%s) created in %s-mode, %s"
                            % (the_app.name, the_app.config.get('VERSION', None),
                               "Debug" if the_app.debug else "Prod", config_string))

    if not no_init:
        init_app(the_app)
    return the_app


def init_app(app):
    if 'initiated' not in app.config:
        # Configure all extensions
        configure_extensions(app)

        # Configure all blueprints
        auth = configure_blueprints(app)

        configure_hooks(app)

        app.config['initiated'] = True


def my_report_exception(app, exception):
    # Modified from rollbar.contrib.flask to automatically insert user data
    if g.user:
        person = {'id': g.user.id, 'email': g.user.email}
    else:
        person = {'id': request.remote_addr if request else 'non-request'}
    rollbar.report_exc_info(request=request, payload_data={'person': person})

def configure_logging(app):
    # Custom logging that always goes to stderr
    import logging
    for h in app.logger.handlers:
        if h.__class__.__name__ == 'ProductionHandler':
            # Override default to error only
            h.setLevel(logging.INFO)
    if app.debug:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    rollbar_token = app.config['ROLLBAR_TOKEN']
    if not app.debug:
        if rollbar_token != 'SECRET':  # SECRET is default, non-set state
            rollbar.init(
                rollbar_token,
                # environment name
                'fablr',
                # server root directory, makes tracebacks prettier
                root=os.path.dirname(os.path.realpath(__file__)),
                # flask already sets up logging
                allow_logging_basic_config=False)

            # send exceptions from `app` to rollbar, using flask's signal system.
            # got_request_exception.connect(rollbar.contrib.flask.report_exception, app)
            got_request_exception.connect(my_report_exception, app)
            rollbar.report_message("Initiated rollbar on %s" % app.config.get('VERSION', None), 'info')
        else:
            app.logger.warning("No ROLLBAR_TOKEN given in config, cannot be started")

        # app.logger.debug("Debug")
        # app.logger.info("Info")
        # app.logger.warn("Warn")
        # app.logger.error("Error")
        # app.logger.info("Info")


def configure_extensions(app):
    import extensions

    app.jinja_env.add_extension('jinja2.ext.do')  # "do" command in jinja to run code
    if not app.debug:
        # Silence undefined errors in templates if not debug
        app.jinja_env.undefined = extensions.SilentUndefined
    # app.jinja_options = ImmutableDict({'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_']})

    app.json_encoder = extensions.MongoJSONEncoder

    app.url_rule_class = extensions.FablrRule
    if 'FLASK_APP' not in os.environ:  # If not set, we are not in local dev server, so we can apply hostname routing
        # Assume we are in a proxy setup and fix headers for that
        app.wsgi_app = ProxyFix(app.wsgi_app)
        prefix = app.config.get('URL_PREFIX', '')
        if prefix:
            app.wsgi_app = extensions.PrefixMiddleware(app.wsgi_app, prefix)
        app.url_rule_class.allow_domains = True
        app.url_rule_class.default_host = app.config['DEFAULT_HOST']
        if app.url_rule_class.default_host:  # Need to have default host to enable host_matching
            app.url_map = Map(host_matching=True)
            # Re-add the static rule
            app.add_url_rule(app.static_url_path + '/<path:filename>', endpoint='static', view_func=app.send_static_file)
            app.logger.info('Doing host matching and default host is {host}{prefix}'.format(
                host=app.url_rule_class.default_host, prefix=prefix))
    else:
        app.logger.warning('Running in local dev mode without hostnames')

    # Rewrites POSTs with specific methods into the real method, to allow HTML forms to send PUT, DELETE, etc
    app.wsgi_app = extensions.MethodRewriteMiddleware(app.wsgi_app)

    extensions.start_db(app)

    # TODO this is a hack to allow authentication via source db admin,
    # will likely break if connection is recreated later
    # mongocfg =   app.config['MONGODB_SETTINGS']
    # db.connection[mongocfg['DB']].authenticate(mongocfg['USERNAME'], mongocfg['PASSWORD'], source="admin")

    # Internationalization
    extensions.babel.init_app(app)  # Automatically adds the extension to Jinja as well
    # Register callback that tells which language to serve
    extensions.babel.localeselector(extensions.pick_locale)
    extensions.configured_locales = set(app.config.get('BABEL_AVAILABLE_LOCALES'))
    if not extensions.configured_locales or app.config.get('BABEL_DEFAULT_LOCALE') not in extensions.configured_locales:
        app.logger.warning('Incorrectly configured: BABEL_DEFAULT_LOCALE %s not in BABEL_AVAILABLE_LOCALES %s' %
                           app.config.get('BABEL_DEFAULT_LOCALE'), app.config.get('BABEL_AVAILABLE_LOCALES'))
        extensions.configured_locales = set([app.config.get('BABEL_DEFAULT_LOCALE')])

    # Secure forms
    extensions.csrf.init_app(app)

    extensions.init_assets(app)

    app.md = Markdown(app, extensions=['attr_list'])
    app.md.register_extension(extensions.AutolinkedImage)

    app.jinja_env.filters['dict_with'] = extensions.dict_with
    app.jinja_env.filters['dict_without'] = extensions.dict_without
    app.jinja_env.filters['currentyear'] = extensions.currentyear

    # Debug toolbar, will stop if DEBUG_TB_ENABLED = False or if not else if DEBUG=False
    extensions.toolbar.init_app(app)


# Dummy function that returns what it was passed
def identity(ob):
    return ob


def configure_blueprints(app):
    with app.app_context():
        from controller.auth import auth_app
        app.register_blueprint(auth_app, url_prefix='/auth')
        app.access_policy = {}

        from controller.asset import asset_app as asset_app
        from controller.world import world_app as world
        from controller.social import social
        from controller.generator import generator
        from controller.admin import admin
        from controller.shop import shop_app as shop
        from controller.mailer import mail_app as mail

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

    # @app.before_request
    # def load_locale():
    #     g.available_locales = available_locales_tuple

    @app.context_processor
    def inject_access():
        return dict(access_policy=app.access_policy, debug=app.debug, assets=app.assets)

    app.add_template_global(get_locale)

    @app.add_template_global
    def in_current_args(testargs):
        if isinstance(testargs, dict):
            for kv in testargs.iteritems():
                # Ignore None-values, they shouldn't be in URL anyway
                if kv[1] is not None and urllib.urlencode([kv]) not in request.query_string:
                    return False
            return True
        else:
            return bool(not [x for x in testargs if x not in request.query_string])

    url_for_args = {'_external', '_anchor', '_method', '_scheme'}

    @app.add_template_global
    def current_url(_multi=False, **kwargs):
        """Returns the current request URL with selected modifications. Set an argument to
        None when calling this to remove it from the current URL"""
        copy_args = request.args.copy()
        non_param_args = kwargs.pop('full_url', False)
        for k, v in kwargs.iteritems():
            if v is None:
                copy_args.poplist(k)
            elif _multi:
                copy_args.setlistdefault(k).append(v)
            else:
                copy_args[k] = v
            non_param_args = non_param_args or (k in request.view_args or k in url_for_args)
        if non_param_args:
            # We have args that will need url_for to build full url
            copy_args.update(request.view_args)  # View args are not including query parameters
            u = url_for(request.endpoint, **copy_args.to_dict())
            return u
        else:
            u = '?' + urllib.urlencode(list(copy_args.iteritems(True)), doseq=True)
            return u
            # We are just changing url parameters, we can do a quicker way

    # @app.errorhandler(404)
    # def not_found(err):
    #     print err
    #     raise err

    @app.errorhandler(ConnectionFailure)
    def db_error(err):
        print err
        raise err
        return "<body>No database</body>", 500

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

    #
    # Print rules in alphabetic order
    # for rule in app.url_map.iter_rules():
    #     print rule.__repr__(), rule.subdomain
    # for rule in sorted(app.url_map.iter_rules(), key=lambda rule: rule.match_compare_key()):
    #   print rule.__repr__(), rule.subdomain, rule.match_compare_key()

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
