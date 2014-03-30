"""
  raconteur.raconteur
  ~~~~~~~~~~~~~~~~

  Main raconteur application class, that initializes the Flask application,
  it's blueprints, plugins and template filters.

  :copyright: (c) 2014 by Raconteur
"""

import os
from flask import Flask, Markup, render_template, request, redirect, url_for, flash, g, make_response, current_app
from flask.json import JSONEncoder
from flask.ext.babel import lazy_gettext as _
from flaskext.markdown import Markdown
from flask.ext.mongoengine import Pagination
from extensions import db, csrf, babel, AutolinkedImage
from mongoengine import Document, QuerySet
from time import gmtime, strftime

# Private = Everything locked down, no access to database (due to maintenance)
# Protected = Site is fully visible. Resources are shown on a case-by-case (depending on default access allowance). Admin is allowed to log in.
# Public = Everyone is allowed to log in and create new accounts
STATE_PRIVATE, STATE_PROTECTED, STATE_PUBLIC = "private", "protected", "public"
STATE_TYPES = ((STATE_PRIVATE, _('Private')),
              (STATE_PROTECTED, _('Protected')),
              (STATE_PUBLIC, _('Public')))

FEATURE_JOIN, FEATURE_CAMPAIGN, FEATURE_SOCIAL, FEATURE_TOOLS = "join", "campaign", "social", "tools"
FEATURE_TYPES = ((FEATURE_JOIN, _('Join')),
                (FEATURE_TOOLS, _('Campaign')),
                (FEATURE_TOOLS, _('Social')),
                (FEATURE_TOOLS, _('Tools')))


app_state = STATE_PUBLIC
app_features = {
  FEATURE_TOOLS: False,
  FEATURE_CAMPAIGN: False,
  FEATURE_SOCIAL: False,
  FEATURE_JOIN: False
}

def is_private():
  return app_state == STATE_PRIVATE


def is_protected():
  return app_state == STATE_PROTECTED


def is_public():
  return app_state == STATE_PUBLIC

def is_allowed_access(user):
  if is_private():
    return False
  elif is_protected():
    return user.admin if user else False
  else:
    return True

class MongoJSONEncoder(JSONEncoder):
  def default(self, o):
    if isinstance(o, Document) or isinstance(o, QuerySet):
      return o.to_json()
    elif isinstance(o, Pagination):
      return {'page':o.page, 'per_page':o.per_page, 'total':o.total}
    return JSONEncoder.default(self, o)

default_options = {
  'MONGODB_SETTINGS': {'DB':'raconteurdb'},
  'SECRET_KEY':'raconteur',
  'DEBUG': True,
  'LANGUAGES': {
    'en': 'English',
    'sv': 'Swedish'
  }
}

def create_app(**kwargs):
  the_app = Flask('raconteur')  # Creates new flask instance
  the_app.config.update(default_options)  # default, dummy settings
  the_app.config.update(kwargs)  # default, dummy settings
  if 'RACONTEUR_CONFIG_FILE' in os.environ:
    the_app.config.from_envvar('RACONTEUR_CONFIG_FILE', silent=True)  # db-settings and secrets, should not be shown in code
  the_app.config['PROPAGATE_EXCEPTIONS'] = the_app.debug
  the_app.json_encoder = MongoJSONEncoder

  configure_logging(the_app)
  the_app.logger.info("App created: %s", the_app)

  # Configure all extensions
  configure_extensions(the_app)

  # Configure all blueprints
  auth = configure_blueprints(the_app)

  configure_hooks(the_app)

  register_main_routes(the_app, auth)

  return the_app

def configure_extensions(app):
  # flask-sqlalchemy
  db.init_app(app)

  # Internationalization
  babel.init_app(app)

  # Secure forms
  csrf.init_app(app)

  md = Markdown(app, extensions=['attr_list'])
  md.register_extension(AutolinkedImage)

def configure_blueprints(app):
  from model.user import User
  from auth import Auth
  auth = Auth(app, db, user_model=User)
  
  with app.app_context():

    from controller.world import world_app as world
    from controller.social import social
    from controller.generator import generator
    from controller.campaign import campaign_app as campaign
    from resource import ResourceError, ResourceHandler, ResourceAccessStrategy, RacModelConverter
    from model.world import ImageAsset

    app.register_blueprint(world, url_prefix='/world')
    if app_features[FEATURE_TOOLS]:
      app.register_blueprint(generator, url_prefix='/generator')
    if app_features[FEATURE_SOCIAL]:
      app.register_blueprint(social, url_prefix='/social')
    if app_features[FEATURE_CAMPAIGN]:
      app.register_blueprint(campaign, url_prefix='/campaign')
  return auth
 
def configure_hooks(app):
  
  @app.before_request
  def load_user():
    g.feature = app_features

def configure_logging(app):
  import logging

  # Set info level on logger, which might be overwritten by handers.
  # Suppress DEBUG messages.
  app.logger.setLevel(logging.INFO if not app.debug else logging.DEBUG)

  print app.logger.name, app.logger.getEffectiveLevel(), app.logger.parent.name

  # info_log = os.path.join(app.config['LOG_FOLDER'], 'info.log')
  # info_file_handler = logging.handlers.RotatingFileHandler(info_log, maxBytes=100000, backupCount=10)
  # info_file_handler.setLevel(logging.INFO)
  # info_file_handler.setFormatter(logging.Formatter(
  #     '%(asctime)s %(levelname)s: %(message)s '
  #     '[in %(pathname)s:%(lineno)d]')
  # )
  # app.logger.addHandler(info_file_handler)


def init_actions(app, init_mode):
  if init_mode:
    if init_mode=='reset':
      setup_models(app)
    elif init_mode=='lang':
      setup_language()
    elif init_mode=='test':
      run_tests()

def setup_models(app):
  app.logger.info("Resetting data models")
  app.logger.info(app.config['MONGODB_SETTINGS'])
  db.connection.drop_database(app.config['MONGODB_SETTINGS']['DB'])
  from test_data import model_setup
  model_setup.setup_models()
  # This hack sets a unique index on the md5 of image files to prevent us from 
  # uploading duplicate images
  # db.connection[the_app.config['MONGODB_SETTINGS']['DB']]['images.files'].ensure_index(
 #        'md5', unique=True, background=True)

def validate_model():
  is_ok = True
  pkgs = ['model.campaign', 'model.misc', 'model.user', 'model.world']  # Look for model classes in these packages
  for doc in db.Document._subclasses:  # Ugly way of finding all document type
    if doc != 'Document':  # Ignore base type (since we don't own it)
      for pkg in pkgs:
        try:
          cls = getattr(__import__(pkg, fromlist=[doc]), doc)  # Do add-hoc import/lookup of type, simillar to from 'pkg' import 'doc'
          try:
            cls.objects()  # Check all objects of type
          except TypeError:
            logger.error("Failed to instantiate %s", cls)
            is_ok = False
        except AttributeError:
          pass  # Ignore errors from getattr
        except ImportError:
          pass  # Ignore errors from __import__
  logger.info("Model has been validated" if is_ok else "Model has errors, aborting startup")
  return is_ok

def setup_language():
  os.system("pybabel compile -d translations/");

def run_tests():
  logger.info("Running unit tests")
  from tests import app_test
  app_test.run_tests()

def register_main_routes(app, auth):
  from flask.ext.mongoengine.wtf import model_form
  from flask.ext.babel import lazy_gettext as _
  from model.user import User
  from model.world import ImageAsset, Article
  from controller.world import ArticleHandler, article_strategy, world_strategy
  from model.web import ApplicationConfig
  from resource import ResourceAccessStrategy, RacModelConverter, ResourceHandler

  @app.route('/')
  def homepage():
    world = world_strategy.query_item(world='helmgast')
    search_result = ArticleHandler(article_strategy).blog({})
    return render_template('world/article_blog.html', parent_template='helmgast.html', articles=search_result['articles'], world=world)

  @app.route('/admin/', methods=['GET', 'POST'])
  @auth.admin_required
  def admin():
    global app_state, app_features

    if request.method == 'GET':
      feature_list = map(lambda (x, y): x, filter(lambda (x, y): y, app_features.items()))
      return render_template('admin.html',
                             config=ApplicationConfig(state=app_state, features=feature_list,
                                                      backup_name=strftime("backup_%Y_%m_%d", gmtime())),
                             databases=db.connection.database_names())
    elif request.method == 'POST':
      config = ApplicationConfig(request.form)
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
          app_features[feature] = feature in config.features.data
      return redirect('/admin/')


  JoinForm = model_form(User)

  # Page to sign up, takes both GET and POST so that it can save the form
  @app.route('/join/', methods=['GET', 'POST'])
  def join():
    if not app_features["join"]:
      raise ResourceError(403)
    if request.method == 'POST' and request.form['username']:
      # Read username from the form that was posted in the POST request
      try:
        User.objects().get(username=request.form['username'])
        flash(_('That username is already taken'))
      except User.DoesNotExist:
        user = User(
            username=request.form['username'],
            email=request.form['email'],
        )
        user.set_password(request.form['password'])
        user.save()

        auth.login_user(user)
        return redirect(url_for('homepage'))
    join_form = JoinForm()
    return render_template('join.html', join_form=join_form)

  @app.route('/asset/<slug>')
  def asset(slug):
    # TODO This should be a lower memory way of doing this
    # try:
    #     file = FS.get(ObjectId(oid))
    #     return Response(file, mimetype=file.content_type, direct_passthrough=True)
    # except NoFile:
    #     abort(404)
    # or this
    # https://github.com/RedBeard0531/python-gridfs-server/blob/master/gridfs_server.py
    asset = ImageAsset.objects(slug=slug).first_or_404()
    response = make_response(asset.image.read())
    response.mimetype = asset.mime_type
    return response

  @app.route('/asset/thumbs/<slug>')
  def asset_thumb(slug):
    asset = ImageAsset.objects(slug=slug).first_or_404()
    response = make_response(asset.image.thumbnail.read())
    response.mimetype = asset.mime_type
    return response

  imageasset_strategy = ResourceAccessStrategy(ImageAsset, 'images', form_class=
    model_form(ImageAsset, exclude=['image','mime_type', 'slug'], converter=RacModelConverter()))
  class ImageAssetHandler(ResourceHandler):
    def new(self, r):
      '''Override new() to do some custom file pre-handling'''
      self.strategy.check_operation_any(r['op'])
      form = self.form_class(request.form, obj=None)
      # del form.slug # remove slug so it wont throw errors here
      if not form.validate():
        r['form'] = form
        raise ResourceError(400, r)
      file = request.files['imagefile']
      item = ImageAsset(creator=g.user)
      if file:
        item.make_from_file(file)
      elif request.form.has_key('source_image_url'):
        item.make_from_url(request.form['source_image_url'])
      else:
        abort(403)
      form.populate_obj(item)
      item.save()
      r['item'] = item
      r['next'] = url_for('asset', slug=item.slug)
      return r
  ImageAssetHandler.register_urls(app, imageasset_strategy)

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
