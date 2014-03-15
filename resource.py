"""
  raconteur.resource
  ~~~~~~~~~~~~~~~~

  An internal library for generating REST-like URL routes and request
  handling functionality for most of Raconteur's models. This provides
  DRYness of code and simplified addition of new models.

  :copyright: (c) 2014 by Raconteur
"""

import inspect
import logging

from flask import request, render_template, flash, redirect, url_for, abort, g
from flask.json import jsonify
from flask.ext.mongoengine.wtf import model_form
from flask.ext.mongoengine.wtf.orm import ModelConverter, converts
from flask.views import View
from wtforms.compat import iteritems
from wtforms import fields as f
from wtforms import Form as OrigForm
from flask.ext.mongoengine.wtf.models import ModelForm
from mongoengine.errors import DoesNotExist, ValidationError, NotUniqueError
from raconteur import is_allowed_access
from model.world import EMBEDDED_TYPES, Article

logger = logging.getLogger(__name__)


def generate_flash(action, name, model_identifiers, dest=''):
  s = u'%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1 else '', ', '.join(model_identifiers), u' to %s' % dest if dest else '')
  flash(s, 'success')
  return s


def error_response(msg, level='error'):
  flash(msg, level)
  return render_template('includes/inline.html')

class ArticleBaseForm(ModelForm):
  def process(self, formdata=None, obj=None, **kwargs):
    super(ArticleBaseForm, self).process(formdata, obj, **kwargs)
    # remove all *article fields that don't match new type
    typedata = Article.type_data_name(self.data.get('type', 'default'))
    for embedded_type in EMBEDDED_TYPES:
      if embedded_type != typedata:
        print 'Removed field %s' % embedded_type
        del self._fields[embedded_type]

  def populate_obj(self, obj):
    if not type(obj) is Article:
      raise TypeError('ArticleBaseForm can only handle Article models')
    if 'type' in self.data:
      new_type = self.data['type']
      # Tell the Article we have changed type
      obj.change_type(new_type)
    super(ArticleBaseForm, self).populate_obj(obj)
    # for name, field in iteritems(self._fields):
    #     # Avoid populating meta fields that are not currently active
    #     if name in EMBEDDED_TYPES and name!=Article.create_type_name(new_type)+'article':
    #         logger = logging.getLogger(__name__)
    #         logger.info("Skipping populating %s, as it's in %s and is != %s", name, EMBEDDED_TYPES, Article.create_type_name(new_type)+'article')
    #         pass
    #     else:
    #         field.populate_obj(obj, name)


class RacModelConverter(ModelConverter):
  @converts('EmbeddedDocumentField')
  def conv_EmbeddedDocument(self, model, field, kwargs):
    kwargs = {
      'validators': [],
      'filters': [],
      'default': field.default or field.document_type_obj,
    }
    # The only difference to normal ModelConverter is that we use the original,
    # insecure WTForms form base class instead of the CSRF enabled one from
    # flask-wtf. This is because we are in a FormField, and it doesn't require
    # additional CSRFs.
    form_class = model_form(field.document_type_obj, converter=RacModelConverter(), base_class=OrigForm, field_args={})
    logger.info("Converted model %s", model)
    return f.FormField(form_class, **kwargs)

  @converts('StringField')
  def conv_String(self, model, field, kwargs):
    if field.regex:
      kwargs['validators'].append(validators.Regexp(regex=field.regex))
    self._string_common(model, field, kwargs)
    if 'password' in kwargs:
      if kwargs.pop('password'):
        return f.PasswordField(**kwargs)
    if field.max_length and field.max_length < 100:
      return f.StringField(**kwargs)
    return f.TextAreaField(**kwargs)


class ResourceAccessStrategy:
  def __init__(self, model_class, plural_name, id_field='id', form_class=None, parent_strategy=None, parent_reference_field=None, short_url=False):
    self.form_class = form_class if form_class else model_form(model_class, converter=RacModelConverter())
    self.model_class = model_class
    self.resource_name = model_class.__name__.lower().split('.')[-1]  # class name, ignoring package name
    self.plural_name = plural_name
    self.parent = parent_strategy
    self.id_field = id_field
    self.short_url = short_url
    self.fieldnames = [n for n in self.form_class.__dict__.keys() if (not n.startswith('_') and n is not 'model_class')]
    # The field name pointing to a parent resource for this resource, e.g. article.world
    self.parent_reference_field = self.parent.resource_name if (self.parent and not parent_reference_field) else None

  def get_url_path(self, part, op=None):
    parent_url = ('' if (self.parent is None) else self.parent.url_item(None))
    op_val = ('' if (op is None) else ('/' + op))
    url = parent_url + '/' + part + op_val
    return url

  def url_list(self, op=None):
    return self.get_url_path(self.plural_name, op)

  def url_item(self, op=None):
    if self.short_url:
      return self.get_url_path('<' + self.resource_name + '>', op)
    else:
      return self.get_url_path(self.plural_name + '/<' + self.resource_name + '>', op)

  def item_template(self):
    return '%s_item.html' % self.resource_name

  def list_template(self):
    return '%s_list.html' % self.resource_name

  def query_item(self, **kwargs):
    id = kwargs[self.resource_name]
    return self.model_class.objects.get(**{self.id_field: id})

  def create_item(self):
    return self.model_class()

  def query_list(self, args):
    qr = self.model_class.objects()
    filters = {}
    for key in args.keys():
      if key == 'order_by':
        qr = qr.order_by(*args.getlist('order_by'))
      else:
        fieldname = key.split('__')[0]
        # print fieldname, (fieldname in self.model_class.__dict__)
        # TODO replace second and-part with dict per model-class that describes what is filterable
        if fieldname[0] != '_' and fieldname in self.model_class.__dict__:
          filters[key] = args.get(key)
    # print filters
    if filters:
      qr = qr.filter(**filters)
    # TODO very little safety in above as all filters are allowed
    return qr

  def query_parents(self, **kwargs):
    if not self.parent:
      return {}
    # Silently pop arg, if existing, relating to current resource
    kwargs.pop(self.resource_name, None)
    grandparents = self.parent.query_parents(**kwargs)
    grandparents[self.parent.resource_name] = self.parent.query_item(**kwargs)
    #print "all parents %s" % grandparents
    return grandparents

  def all_view_args(self, item):
    view_args = {self.resource_name : getattr(item, self.id_field)}
    if self.parent:
      view_args.update(self.parent.all_view_args(getattr(item, self.parent_reference_field)))
    return view_args

  def endpoint_name(self, suffix):
    return self.resource_name + '_' + suffix

  def allowed(self, op, instance=None):
    # If instance exists, check allowed on that, otherwise check on model class
    return is_allowed_access(g.user) \
      and (g.user is not None or op in ["view", "list"]) \
      and (self.parent.allowed(op, instance) if self.parent else True)

  def allowed_any(self, op):
    return self.allowed(op, None)

  def allowed_on(self, op, instance):
    return self.allowed(op, instance)


class AdminWriteResourceAccessStrategy(ResourceAccessStrategy):
	def allowed(self, op, instance=None):
		super(ResourceAccessStrategy, self).allowed(op, instance) \
			and (g.user is not None and g.user.admin and op not in ["view", "list"])


class ResourceError(Exception):
  logger = logging.getLogger(__name__)

  default_messages = {
    400: "Bad request or invalid input",
    401: "Unathorized access, please login",
    403: "Forbidden, this is not an allowed operation",
    404: "Resource not found",
    500: "Internal server error"
  }

  def __init__(self, status_code, r=None, message=None):
    Exception.__init__(self)
    self.status_code = status_code
    self.message = message if message else self.default_messages.get(status_code, 'Unknown error')
    if status_code == 400 and r and 'form' in r:
      self.message += ", invalid fields %s" % r['form'].errors.keys()
    self.r = r
    logger.warning("%d: %s", self.status_code, self.message)

  def to_dict(self):
    rv = dict()
    rv['message'] = self.message
    rv['status_code'] = self.status_code
    return rv


class ResourceHandler(View):
  default_ops = ['view', 'form_new', 'form_edit', 'list', 'new', 'replace', 'edit', 'delete']
  ignored_methods = ['as_view', 'dispatch_request', 'parse_url', 'register_urls']
  get_post_pairs = {'edit':'form_edit', 'new':'form_new','replace':'form_edit', 'delete':'edit'}
  logger = logging.getLogger(__name__)

  def __init__(self, strategy):
    self.form_class = strategy.form_class
    self.strategy = strategy

  @classmethod
  def register_urls(cls, app, st):
    # We try to parse out any methods added to this handler class, which we will use as separate endpoints
    custom_ops = []
    for name, m in inspect.getmembers(cls, predicate=inspect.ismethod):
      if (not name.startswith("__")) and (not name in cls.ignored_methods) and (not name in cls.default_ops):
        app.add_url_rule(st.get_url_path(name), methods=['GET'], view_func=cls.as_view(st.endpoint_name(name), st))
        custom_ops.append(name)

    logger.info("Creating resource with url pattern %s and custom ops %s", st.url_item(), [st.get_url_path(o) for o in custom_ops])

    app.add_url_rule(st.url_item(), methods=['GET'], view_func=cls.as_view(st.endpoint_name('view'), st))
    app.add_url_rule(st.url_list('new'), methods=['GET'], view_func=cls.as_view(st.endpoint_name('form_new'), st))
    # app.add_url_rule(st.url_list('edit'), methods=['GET'], view_func=ResourceHandler.as_view(st.endpoint_name('get_edit_list'), st))
    app.add_url_rule(st.url_item('edit'), methods=['GET'], view_func=cls.as_view(st.endpoint_name('form_edit'), st))
    app.add_url_rule(st.url_list(), methods=['GET'], view_func=cls.as_view(st.endpoint_name('list'), st))
    app.add_url_rule(st.url_list(), methods=['POST'], view_func=cls.as_view(st.endpoint_name('new'), st))
    app.add_url_rule(st.url_item(), methods=['PUT', 'POST'], view_func=cls.as_view(st.endpoint_name('replace'), st))
    app.add_url_rule(st.url_item(), methods=['PATCH', 'POST'], view_func=cls.as_view(st.endpoint_name('edit'), st))
    app.add_url_rule(st.url_item(), methods=['DELETE', 'POST'], view_func=cls.as_view(st.endpoint_name('delete'), st))

  def dispatch_request(self, *args, **kwargs):
    # If op is given by argument, we use that, otherwise we take it from endpoint
    # The reason is that endpoints are not unique, e.g. for a given URL there may be many endpoints
    # TODO unsafe to let us call a custom methods based on request args!
    r = self.parse_url(**kwargs)
    try:
      r = self.query_url_components(r, **kwargs)
      r = getattr(self, r['op'])(r)  # picks the right method from the class and calls it!
    except ResourceError as err:
      if err.status_code == 400: # bad request
        if r['op'] in self.get_post_pairs:
          # we were posting a form
          r['op'] = self.get_post_pairs[r['op']] # change the effective op
          r['template'] = self.strategy.item_template()
          r[self.strategy.resource_name + '_form'] = r['form']

        # if json, return json instead of render
        if r['out'] == 'json':
          return self.return_json(r, err)
        else:
          flash(err.message,'warning')
          return render_template(r['template'], **r), 400

      elif err.status_code == 401: # unauthorized
        if r['out'] == 'json':
          return self.return_json(r, err)
        else:
          flash(err.message,'warning')
          # if fragment/json, just return 401
          return redirect(url_for('auth.login', next=request.path))

      elif err.status_code == 403: # forbidden
        r['op'] = self.get_post_pairs[r['op']] # change the effective op
        r['template'] = self.strategy.item_template()
        r[self.strategy.resource_name + '_form'] = form
        # if json, return json instead of render
        if r['out'] == 'json':
          return self.return_json(r, err)
        else:
          flash(err.message,'warning')
          return render_template(r['template'], **r), 403

      elif err.status_code == 404:
        abort(404) # TODO, nicer 404 page?

      elif r['out'] == 'json':
        return self.return_json(r, err)
      else:
        raise # Send the error onward, will be picked up by debugger if in debug mode
    except DoesNotExist:
      abort(404)
    except ValidationError as err:
      self.logger.exception("Validation error")
      resErr = ResourceError(400, message=err.message)
      if r['out'] == 'json':
        return self.return_json(r, resErr)
      else:
        raise resErr # Send the error onward, will be picked up by debugger if in debug mode
    except NotUniqueError as err:
      resErr = ResourceError(400, message=err.message)
      if r['out'] == 'json':
        return self.return_json(r, resErr)
      else:
        raise resErr # Send the error onward, will be picked up by debugger if in debug mode



    # render output
    if r['out'] == 'json':
      return self.return_json(r)
    elif 'next' in r:
      return redirect(r['next'])
    else:
      # if json, return json instead of render
      return render_template(r['template'], **r)

  def return_json(self, r, err=None, status_code=0):
    if err:
      return jsonify(err.to_dict()), status_code or err.status_code
    else:
      return jsonify({k:v for k,v in r.iteritems() if k in ['item','list','op','parents','next']})

  def parse_url(self, **kwargs):
    r = {'url_args':kwargs}
    op = request.args.get('op', request.endpoint.split('.')[-1].split('_',1)[-1].lower())
    if op in ['form_edit', 'form_new','list']:
      # TODO faster, more pythonic way of getting intersection of fieldnames and args
      vals = {}
      for arg in request.args:
        if arg in self.strategy.fieldnames:
          val = request.args.get(arg).strip()
          if val:
            vals[arg] = val
      r['filter' if op is 'list' else 'prefill'] = vals
    r['op'] = op
    r['out'] = request.args.get('out','html') # default to HTML
    if 'next' in request.args:
      r['next'] = request.args['next']
    return r

  def query_url_components(self, r, **kwargs):
    if self.strategy.resource_name in kwargs:
      r['item'] = self.strategy.query_item(**kwargs)
      r[self.strategy.resource_name] = r['item']
    r['parents'] = self.strategy.query_parents(**kwargs)
    r.update(r['parents'])
    return r

  def view(self, r):
    item = r['item']
    if not self.strategy.allowed_on(r['op'], item):
      raise ResourceError(401)
    r['template'] = self.strategy.item_template()
    return r

  def form_edit(self, r):
    item = r['item']
    if not item:
      raise ResourceError(500)
    if not self.strategy.allowed_on(r['op'], item):
      raise ResourceError(401)
    form = self.form_class(obj=item, **r.get('prefill',{}))
    form.action_url = url_for('.' + self.strategy.endpoint_name('edit'), op='edit', **r['url_args'])
    r[self.strategy.resource_name + '_form'] = form
    r['op'] = 'edit' # form_edit is not used in templates...
    r['template'] = self.strategy.item_template()
    return r

  def form_new(self, r):
    if not self.strategy.allowed_any(r['op']):
      raise ResourceError(401)
    form = self.form_class(request.args, obj=None, **r.get('prefill',{}))
    form.action_url = url_for('.' + self.strategy.endpoint_name('new'), **r['url_args'])
    r[self.strategy.resource_name + '_form'] = form
    r['op'] = 'new' # form_new is not used in templates...
    r['template'] = self.strategy.item_template()
    return r

  def list(self, r):
    if not self.strategy.allowed_any(r['op']):
      raise ResourceError(401)
    r['list'] = self.strategy.query_list(request.args).filter(**r.get('filter',{}))
    r['template'] = self.strategy.list_template()
    r[self.strategy.plural_name] = r['list']
    return r

  def new(self, r):
    if not self.strategy.allowed_any(r['op']):
      raise ResourceError(401)
    form = self.form_class(request.form, obj=None)
    if not form.validate():
      r['form'] = form
      raise ResourceError(400, r)
    item = self.strategy.create_item()
    form.populate_obj(item)
    item.save()
    r['item'] = item
    if not 'next' in r:
      r['next'] = url_for('.' + self.strategy.endpoint_name('view'), **self.strategy.all_view_args(item))
    return r

  # TODO implement proper patch, currently just copy of PUT
  def edit(self, r):
    item = r['item']
    if not item:
      raise ResourceError(500)
    if not self.strategy.allowed_on(r['op'], item):
      raise ResourceError(401)
    form = self.form_class(request.form, obj=item)
    if not form.validate():
      r['form'] = form
      raise ResourceError(400, r)
    form.populate_obj(item)
    item.save()
    # In case slug has changed, query the new value before redirecting!
    if not 'next' in r:
      r['next'] = url_for('.' + self.strategy.endpoint_name('view'), **self.strategy.all_view_args(item))
    self.logger.info("Edit on %s/%s", self.strategy.resource_name, item.slug)
    return r

  def replace(self, r):
    item = r['item']
    if not item:
      raise ResourceError(500)
    if not self.strategy.allowed_on(r['op'], item):
      raise ResourceError(401)
    form = self.form_class(request.form, obj=item)
    # self.print_form_inputs(request.form, form.data, item)
    if not form.validate():
      r['form'] = form
      raise ResourceError(400, r)
    form.populate_obj(item)
    item.save()
    if not 'next' in r:
      # In case slug has changed, query the new value before redirecting!
      r['next'] = url_for('.' + self.strategy.endpoint_name('view'), **self.strategy.all_view_args(item))
    return r

  def delete(self, r):
    item = r['item']
    if not item:
      raise ResourceError(500)
    if not self.strategy.allowed_on(r['op'], item):
      raise ResourceError(401)
    if not 'next' in r:
      if 'parents' in r:
        r['next'] = url_for('.' + self.strategy.endpoint_name('list'), **self.strategy.parent.all_view_args(getattr(item, self.strategy.parent_reference_field)))
      else:
        r['next'] = url_for('.' + self.strategy.endpoint_name('list'))
    if not self.strategy.allowed_on(r['op'], item):
      raise ResourceError(401)
    self.logger.info("Delete on %s with id %s", self.strategy.resource_name, item.id)
    item.delete()
    return r

