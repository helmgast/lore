"""
  fablr.app
  ~~~~~~~~~~~~~~~~

  Main Fablr application class, that initializes the Flask application,
  it's blueprints, plugins and template filters.

  :copyright: (c) 2014 by Helmgast AB
"""

import os
from datetime import datetime
import time
from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask.ext.babel import lazy_gettext as _
from flaskext.markdown import Markdown

# Private = Everything locked down, no access to database (due to maintenance)
# Protected = Site is fully visible. Resources are shown on a case-by-case (depending on default access allowance).
#  Admin is allowed to log in.
# Public = Everyone is allowed to log in and create new accounts
STATE_PRIVATE, STATE_PROTECTED, STATE_PUBLIC = "private", "protected", "public"
STATE_TYPES = ((STATE_PRIVATE, _('Private')),
               (STATE_PROTECTED, _('Protected')),
               (STATE_PUBLIC, _('Public')))

FEATURE_JOIN, FEATURE_CAMPAIGN, FEATURE_SOCIAL, FEATURE_TOOLS, FEATURE_SHOP = 'join', 'campaign', 'social', 'tools', \
                                                                              'shop'

FEATURE_TYPES = ((FEATURE_JOIN, _('Join')),
                 (FEATURE_CAMPAIGN, _('Campaign')),
                 (FEATURE_SOCIAL, _('Social')),
                 (FEATURE_TOOLS, _('Tools')),
                 (FEATURE_SHOP, _('Shop'))
                 )

app_state = STATE_PUBLIC
app_features = {
    FEATURE_TOOLS: False,
    FEATURE_CAMPAIGN: False,
    FEATURE_SOCIAL: True,
    FEATURE_JOIN: False,
    FEATURE_SHOP: True
}


def is_private():
    return app_state == STATE_PRIVATE


def is_protected():
    return app_state == STATE_PROTECTED


def is_public():
    return app_state == STATE_PUBLIC


def create_app(no_init=False, **kwargs):
    the_app = Flask('fablr')  # Creates new flask instance
    config_string = "config from:"
    import default_config
    the_app.config.from_object(default_config.Config)  # Default config that applies to all deployments
    the_app.config.from_object(default_config.SecretConfig)  # Add dummy secrets
    try:
        the_app.config.from_pyfile('config.py', silent=False)  # Now override with custom settings if exist
        config_string += " file config.py, "
    except IOError:
        pass
    the_app.config.from_pyfile('version.cfg', silent=True)

    # Override defaults with any environment variables, as long as they are defined in default.
    # TODO there could be name collision with env variables, and this may be unsafe
    env_config = []
    for k in the_app.config.iterkeys():
        env_k = 'FABLR_%s' % k
        if env_k in os.environ and os.environ[env_k]:
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

        register_main_routes(app, auth)
        app.config['initiated'] = True


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

        # app.logger.debug("Debug")
        # app.logger.info("Info")
        # app.logger.warn("Warn")
        # app.logger.error("Error")
        # app.logger.info("Info")


def configure_extensions(app):
    import extensions
    app.jinja_env.add_extension('jinja2.ext.do')  # "do" command in jina to run code
    if not app.debug:
        # Silence undefined errors in templates if not debug
        app.jinja_env.undefined = extensions.SilentUndefined
    # app.jinja_options = ImmutableDict({'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_']})

    app.wsgi_app = extensions.MethodRewriteMiddleware(app.wsgi_app)

    app.json_encoder = extensions.MongoJSONEncoder

    # @app.url_defaults
    # def default_publisher(endpoint, values):
    #     if 'publisher' in values:
    #         return
    #     else:
    #         values['publisher'] = 'helmgast'

    # app.url_map.host_matching = True
    # app.url_map.default_subdomain = 'fablr.local'

    # def host_in_url(endpoint, values):
    #     print "setting host from %s to %s" % (values.get('host', ''), 'sub')
    #     values.setdefault('host', 'sub')

    # app.url_defaults(host_in_url)

    extensions.start_db(app)

    # TODO this is a hack to allow authentication via source db admin,
    # will likely break if connection is recreated later
    # mongocfg =   app.config['MONGODB_SETTINGS']
    # db.connection[mongocfg['DB']].authenticate(mongocfg['USERNAME'], mongocfg['PASSWORD'], source="admin")

    # Internationalization
    extensions.babel.init_app(app)  # Automatically adds the extension to Jinja as well
    # Register callback that tells which language to serve
    extensions.babel.localeselector(extensions.get_locale)

    # Secure forms
    extensions.csrf.init_app(app)

    app.md = Markdown(app, extensions=['attr_list'])
    app.md.register_extension(extensions.AutolinkedImage)

    # Debug toolbar
    if app.config.get('DEBUG_TB_ENABLED', False):
        extensions.toolbar.init_app(app)


def configure_blueprints(app):
    with app.app_context():
        from model.user import User, ExternalAuth
        from controller.auth import Auth
        from extensions import db
        auth = Auth(app, db, user_model=User, ext_auth_model=ExternalAuth)

        from controller.asset import asset_app as asset_app
        from controller.world import world_app as world
        from controller.social import social
        from controller.generator import generator
        from controller.campaign import campaign_app as campaign
        from controller.shop import shop_app as shop
        from controller.mailer import mail_app as mail

        app.register_blueprint(world)
        app.register_blueprint(generator, url_prefix='/generator')
        app.register_blueprint(social, url_prefix='/social')
        app.register_blueprint(campaign, url_prefix='/campaign')
        app.register_blueprint(shop, url_prefix='/shop')
        app.register_blueprint(asset_app, url_prefix='/assets')
        app.register_blueprint(mail, url_prefix='/mail')
        import mandrill
        mail.mandrill_client = mandrill.Mandrill(app.config['MANDRILL_API_KEY'])

    return auth


def configure_hooks(app):
    @app.before_request
    def load_user():
        g.feature = app_features

    @app.add_template_global
    def current_url(**kwargs):
        """Returns the current request URL with selected modifications. Set an argument to
        None when calling this to remove it from the current URL"""
        copy_args = request.view_args.copy()
        copy_args.update(request.args)  # View args are not including query parameters
        copy_args.update(kwargs)
        copy_args = {k: v for k, v in copy_args.iteritems() if v is not None}
        return url_for(request.endpoint, **copy_args)

    @app.context_processor
    def inject_access():
        return dict(access_policy=app.access_policy)


def register_main_routes(app, auth):
    from controller.resource import ResourceError
    from model.misc import ApplicationConfigForm
    from extensions import db

    @app.route('/admin/', methods=['GET', 'POST'])
    @auth.admin_required
    def admin():
        global app_state, app_features

        if request.method == 'GET':
            feature_list = map(lambda (x, y): x, filter(lambda (x, y): y, app_features.items()))
            config = ApplicationConfigForm(state=app_state, features=feature_list,
                                           backup_name=time.time().strftime("backup_%Y_%m_%d"))
            return render_template('admin.html', config=config)
            # Requires additional auth, so skipped now
            # databases=db.connection.database_names())
        elif request.method == 'POST':
            config = ApplicationConfigForm(request.form)
            if not config.validate():
                raise Exception("Bad request data")
            if config.backup.data:
                if config.backup_name.data in db.connection.database_names():
                    raise Exception("Name already exists")
                app.logger.info("Copying current database to '%s'", config.backup_name.data)
                db.connection.copy_database('raconteurdb', config.backup_name.data)
            if config.state.data:
                app_state = config.state.data
            if config.features.data is not None:
                for feature in app_features:
                    is_enabled = feature in config.features.data
                    app_features[feature] = is_enabled
            return redirect('/admin/')

    @app.errorhandler(ResourceError)
    def resource_error(err):
        # if request.args.has_key('debug') and current_app.debug:
        #     raise # send onward if we are debugging

        if err.status_code == 400:  # bad request
            if err.template:
                flash(err.message, 'warning')
                return render_template(err.template, **err.template_vars), err.status_code
        raise err  # re-raise if we don't have a template

    @app.template_filter('currentyear')
    def currentyear():
        return datetime.utcnow().strftime('%Y')

    @app.template_filter('dict_without')
    def dict_without(value, *args):
        return {k: value[k] for k in value.keys() if k not in args}

    @app.template_filter('dict_with')
    def dict_with(value, **kwargs):
        z = value.copy()
        z.update(kwargs)
        return z

    @app.before_request
    def before_request():
        g.start = time.time()

    @app.teardown_request
    def teardown_request(exception=None):
        if 'start' in g:
            diff = time.time() - g.start
            if diff > 500:
                app.logger.warning("Request %s took %i ms to serve" % (request.url, diff))

    # Print rules in alphabetic order
    # for rule in sorted(app.url_map.iter_rules(), key=lambda rule: rule.rule):
    #   print rule.__repr__(), rule.subdomain

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
