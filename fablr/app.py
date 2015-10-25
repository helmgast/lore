"""
  fablr.app
  ~~~~~~~~~~~~~~~~

  Main Fablr application class, that initializes the Flask application,
  it's blueprints, plugins and template filters.

  :copyright: (c) 2014 by Helmgast AB
"""

import os, sys
from flask import Flask, Markup, render_template, request, redirect, url_for, flash, g, make_response, current_app, abort
from flask.ext.babel import lazy_gettext as _
from flaskext.markdown import Markdown
from extensions import db, start_db, csrf, babel, AutolinkedImage, MongoJSONEncoder, SilentUndefined, toolbar
from time import gmtime, strftime

# Private = Everything locked down, no access to database (due to maintenance)
# Protected = Site is fully visible. Resources are shown on a case-by-case (depending on default access allowance). Admin is allowed to log in.
# Public = Everyone is allowed to log in and create new accounts
STATE_PRIVATE, STATE_PROTECTED, STATE_PUBLIC = "private", "protected", "public"
STATE_TYPES = ((STATE_PRIVATE, _('Private')),
              (STATE_PROTECTED, _('Protected')),
              (STATE_PUBLIC, _('Public')))

FEATURE_JOIN, FEATURE_CAMPAIGN, FEATURE_SOCIAL, FEATURE_TOOLS, FEATURE_SHOP = 'join', 'campaign', 'social', 'tools', 'shop'
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
  the_app = Flask('fablr', static_url_path='/fablr/static')  # Creates new flask instance
  config_string = "default config"
  import default_config
  the_app.config.from_object(default_config.Config) # Default config that applies to all deployments
  the_app.config.from_object(default_config.SecretConfig) # Add dummy secrets
  try:
      the_app.config.from_pyfile('config.py', silent=False) # Now override with custom settings if exist
      config_string += ", file config.py"
  except IOError as err:
      pass

  # Override defaults with any environment variables, as long as they are defined in default.
  # TODO there could be name collision with env variables, and this may be unsafe
  env_config = []
  for k in the_app.config.iterkeys():
    env_k = 'FABLR_%s' % k
    if env_k in os.environ and os.environ[env_k]:
      the_app.config[k] = os.environ[env_k]
      env_config.append(k)
  if env_config:
    config_string += ", env: %s" % ','.join(env_config)

  the_app.config.update(kwargs)  # add any overrides from startup command
  the_app.config['PROPAGATE_EXCEPTIONS'] = the_app.debug

  # If in production, make sure we don't have any dummy secrets
  if not the_app.debug:
    for key in dir(default_config.SecretConfig):
      if key.isupper():
        if the_app.config[key] == 'SECRET':
          raise ValueError("Secret key %s given dummy value in production - ensure"+
            " it's overriden. Config method: %s" % (key,config_string))

  configure_logging(the_app)
  the_app.logger.info("Flask '%s' (%s) started, %s" \
    % (the_app.name, the_app.config.get('VERSION',None), config_string))
  if not no_init:
      init_app(the_app)
  return the_app

def init_app(app):
  if not 'initiated' in app.config:
    # Configure all extensions
    configure_extensions(app)

    # Configure all blueprints
    auth = configure_blueprints(app)

    configure_hooks(app)

    register_main_routes(app, auth)
    app.config['initiated'] = True

def configure_logging(app):
  import logging
  app.debug_log_format = '[%(asctime)s] %(levelname)s in %(filename)s:%(lineno)d: %(message)s'
  # Basic app logger will only log when debug is True, otherwise ignore all errors
  # This is to keep stderr clean in server application scenarios
  # app.logger.setLevel(logging.INFO)

def configure_extensions(app):
  app.jinja_env.add_extension('jinja2.ext.do') # "do" command in jina to run code
  app.jinja_env.undefined = SilentUndefined
  # app.jinja_options = ImmutableDict({'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_']})

  app.json_encoder = MongoJSONEncoder

  start_db(app)

  # TODO this is a hack to allow authentication via source db admin,
  # will likely break if connection is recreated later
  # mongocfg =   app.config['MONGODB_SETTINGS']
  # db.connection[mongocfg['DB']].authenticate(mongocfg['USERNAME'], mongocfg['PASSWORD'], source="admin")

  # Internationalization
  babel.init_app(app) # Automatically adds the extension to Jinja as well

  # Secure forms
  csrf.init_app(app)

  app.md = Markdown(app, extensions=['attr_list'])
  app.md.register_extension(AutolinkedImage)

  # Debug toolbar
  toolbar.init_app(app)

def configure_blueprints(app):

  with app.app_context():
    from model.user import User, ExternalAuth
    from controller.auth import Auth
    auth = Auth(app, db, user_model=User, ext_auth_model=ExternalAuth)

    from controller.asset import asset_app as asset_app
    from controller.world import world_app as world
    from controller.social import social
    from controller.generator import generator
    from controller.campaign import campaign_app as campaign
    from controller.shop import shop_app as shop
    from controller.mailer import mail_app as mail
    from controller.resource import ResourceError, ResourceHandler, ResourceRoutingStrategy, RacModelConverter
    from model.world import ImageAsset

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

  @app.context_processor
  def inject_access():
    return dict(access_policy=app.access_policy)

def register_main_routes(app, auth):
  from flask.ext.mongoengine.wtf import model_form
  from flask.ext.babel import lazy_gettext as _
  from model.user import User
  from model.shop import Order
  from model.world import Article
  from controller.world import ArticleHandler, article_strategy, world_strategy
  from model.web import ApplicationConfigForm

  @app.route('/')
  def homepage():
    world = world_strategy.query_item(world='helmgast')
    search_result = ArticleHandler(article_strategy).blog({'parents':{'world':world}})
    return render_template('helmgast.html', articles=search_result['articles'], world=world)
    # return render_template('world/article_blog.html', parent_template='helmgast.html', articles=search_result['articles'], world=world)

  @app.route('/admin/', methods=['GET', 'POST'])
  @auth.admin_required
  def admin():
    global app_state, app_features

    if request.method == 'GET':
      feature_list = map(lambda (x, y): x, filter(lambda (x, y): y, app_features.items()))
      config = ApplicationConfigForm(state=app_state, features=feature_list,
                                 backup_name=strftime("backup_%Y_%m_%d", gmtime()))
      return render_template('admin.html', config=config)
                            # Requires additional auth, so skipped now
                             #databases=db.connection.database_names())
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
      if not config.features.data is None:
        for feature in app_features:
          is_enabled = feature in config.features.data
          app_features[feature] = is_enabled
      return redirect('/admin/')

  @app.template_filter('currentyear')
  def currentyear():
    return datetime.utcnow().strftime('%Y')

  @app.template_filter('without')
  def without(value, *args):
    return {k:value[k] for k in value.keys() if k not in args}


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
