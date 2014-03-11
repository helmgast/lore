"""
    controller.world
    ~~~~~~~~~~~~~~~~

    This is the controller and Flask blueprint for game world features,
    it initializes URL routes based on the Resource module and specific
    ResourceAccessStrategy for each world related model class. This module is then
    responsible for taking incoming URL requests, parse their parameters,
    perform operations on the Model classes and then return responses via 
    associated template files.

    :copyright: (c) 2014 by Raconteur
"""

from flask import request, redirect, url_for, render_template, Blueprint, flash, make_response, g, abort
from model.world import (Article, World, ArticleRelation, PersonData, PlaceData, 
  EventData, ImageData, FractionData)
from model.user import Group
from flask.views import View
from flask.ext.mongoengine.wtf import model_form, model_fields
from collections import OrderedDict

from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter, ArticleBaseForm
from raconteur import auth, db, csrf
from itertools import groupby
from datetime import datetime, timedelta
from wtforms.fields import FieldList, HiddenField
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

world_app = Blueprint('world', __name__, template_folder='../templates/world')

world_strategy = ResourceAccessStrategy(World, 'worlds', 'slug', short_url=True)

class WorldHandler(ResourceHandler):
  def myworlds(self, r):
    # Worlds which this user has created articles for
    # TODO probably not efficient if many articles!
    arts = Article.objects(creator=g.user).only("world").select_related()
    worlds = [a.world for a in arts]
    r['template'] = self.strategy.list_template()
    r[self.strategy.plural_name] = worlds
    return r    

WorldHandler.register_urls(world_app, world_strategy)

class ArticleHandler(ResourceHandler):
  def blog(self, r):
    r = self.list(r)
    r['template'] = 'world/article_blog.html'
    r['list'] = r['list'].filter(type='blog').order_by('-created_date')
    r['articles'] = r['list']
    return r

  def form_new(self, r):
    r = super(ArticleHandler, self).form_new(r)
    if 'prefill' in r and 'type' in r['prefill']:
      type = r['prefill']['type']
      if type=='image':
        r['template'] = 'world/image_new.html' # change to image template
    return r


article_strategy = ResourceAccessStrategy(Article, 'articles', 'slug', parent_strategy=world_strategy, 
  form_class = model_form(Article, base_class=ArticleBaseForm, exclude=['slug'], converter=RacModelConverter()), short_url=True)
ArticleHandler.register_urls(world_app, article_strategy)

article_relation_strategy = ResourceAccessStrategy(ArticleRelation, 'relations', None, parent_strategy=article_strategy)

ResourceHandler.register_urls(world_app, article_relation_strategy)

@world_app.route('/')
def index():
    worlds = World.objects()
    return render_template('world/world_list.html', worlds=worlds)

@world_app.route('/images/<slug>')
def image(slug):
  imagedata= Article.objects(slug=slug).first_or_404().imagedata
  response = make_response(imagedata.image.read())
  response.mimetype = imagedata.mime_type or 'image/jpeg'
  return response

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

#@auth.login_required
@world_app.route('/images/<world>/new', methods=['POST'])
def insert_image(world):
  print request.form
  world = World.objects.get(slug=world)
  if request.method == 'POST':
    file = request.files['imagefile']
    im = None
    if file and file.filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS:
      fname = secure_filename(file.filename)
      print "got file %s" % fname
      im = ImageData()
      im.image.put(file)
      im.mime_type = request.form['imagedata-mime_type']
    elif request.form.has_key('imagedata.source_image_url'):
      im = ImageData.create_from_url(request.form['imagedata.source_image_url'])
    else:
      abort(403)
    if im:
      article = Article(type='image',
        title=request.form['title'],
        world=world,
        creator=g.user,
        imagedata=im).save()
      return url_for('world.image', slug=article.slug) # TODO HACKY WAY OF GETTING URL BACK TO MODAL

def rows(objects, char_per_row=40, min_rows=10):
  found = 0
  if objects and isinstance(objects, str):
    start, end = 0, min(char_per_row, len(objects))
    while(start<len(objects)):
      i = objects.find('\n', start, end)
      found += 1
      logger = logging.getLogger(__name__)
      logger.info("Reading char %i-%i, got %i, found %i", start, end-1, i, found)
      if i==-1:
        start = end
        end = end+char_per_row
      else:
        start = i+1
        end = start+char_per_row
  return max(found,min_rows)


# Template filter, will group a list by their initial title letter
def by_initials(objects):
  groups = []
  for k, g in groupby(sorted(objects, key=lambda x : x.title.upper()), lambda o: o.title[0:1].upper()):
    groups.append({'grouper':k, 'list':list(g)})
  return sorted(groups, key=lambda x : x['grouper'])

# Template filter, will group a list by their article type_name
def by_articletype(objects):
  groups = []
  for k, g in groupby(sorted(objects, key=lambda x : x.type), lambda o: o.type):
    groups.append({'grouper':k, 'list':sorted(list(g), key=lambda x : x.title)})
  return sorted(groups, key=lambda x : x['grouper'])

def prettydate(d):
  diff = timedelta()
  diff = datetime.utcnow() - d
  if diff.days < 1:
      return 'Today'
  elif diff.days < 7:
      return 'Last week'
  elif diff.days < 31:
      return 'Last month'
  elif diff.days < 365:
      return 'Last year'
  else:
        return 'Older'

# Template filter, will group a list by creation date, as measure in delta from now
def by_time(objects):
  groups = []
  for k, g in groupby(sorted(objects, key=lambda x : x.created_date), lambda o: prettydate(o.created_date)):
    groups.append({'grouper':k, 'list':sorted(list(g), key=lambda x : x.title)})
  return sorted(groups, key=lambda x : x['list'][0].created_date, reverse=True)

world_app.add_app_template_filter(by_initials)
world_app.add_app_template_filter(by_articletype)
world_app.add_app_template_filter(by_time)
world_app.add_app_template_filter(rows)
