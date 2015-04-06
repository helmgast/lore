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
import sys
import re

from flask import request, render_template, flash, redirect, url_for, abort, g, current_app
from flask import current_app as the_app
from flask.json import jsonify
from flask.ext.mongoengine.wtf import model_form
from flask.ext.mongoengine.wtf.orm import ModelConverter, converts
from flask.ext.mongoengine.wtf.fields import ModelSelectField
from flask.views import View
from flask.ext.babel import lazy_gettext as _
from wtforms.compat import iteritems
from wtforms import fields as f
from wtforms import Form as OrigForm
from flask.ext.mongoengine.wtf.models import ModelForm
from mongoengine.errors import DoesNotExist, ValidationError, NotUniqueError
from raconteur import is_allowed_access
from model.world import EMBEDDED_TYPES, Article

logger = current_app.logger if current_app else logging.getLogger(__name__)

objid_matcher = re.compile(r'^[0-9a-fA-F]{24}$')

def generate_flash(action, name, model_identifiers, dest=''):
  s = u'%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1 
    else '', ', '.join(model_identifiers), u' to %s' % dest if dest else '')
  flash(s, 'success')
  return s

def parse_out_arg(out_param):
  if out_param == 'json':
    return out_param
  elif out_param in ['page', 'modal', 'fragment']:
    return '_%s.html' % out_param  # to use as template path
                          # used in Jinja
  else:
    return None # Same as page, but set as None in order to not override template given inheritance

def error_response(msg, level='error'):
  flash(msg, level)
  return render_template('includes/inline.html')

class RacBaseForm(ModelForm):
  def populate_obj(self, obj, fields_to_populate=None):
    if fields_to_populate:
      # FormFields in form args will have '-' do denote it's subfields. We 
      # only want the first part, or it won't match the field names
      fields_to_populate = set([fld.split('-',1)[0] for fld in fields_to_populate])
      newfields = [ (name,fld) for (name,fld) in iteritems(self._fields) if name in fields_to_populate]
    else:
      newfields = iteritems(self._fields)
    for name, field in newfields:
      if ( isinstance(field, f.FormField)
        and getattr(obj, name, None) is None
        and field._obj is None ):
        field._obj = field.model_class()
      field.populate_obj(obj, name)

# class PartialEditForm(OrigForm):
#   def populate_obj(self, obj, fields_to_populate=None):
#     if fields_to_populate:
#       # FormFields in form args will have '-' do denote it's subfields. We 
#       # only want the first part, or it won't match the field names
#       fielddict = {}
#       for fld in fields_to_populate:
#         fld = fld.split('-',1)
#         subfields = fielddict.setdefault(fld[0], [])
#         if len(fld)>1:
#           subfields.append(fld[1])
#       # fields_to_populate = set([fld.split('-',1)[0] for fld in fields_to_populate])
#       newfields = [ (name,fld) for (name,fld) in iteritems(self._fields) if name in fields_to_populate]
#     else:
#       newfields = iteritems(self._fields)
#     for name, field in newfields:
#       if isinstance(field, PartialEditForm):
#         subfields_to_populate = None
#         if isinstance(field, f.FormField):
#           if getattr(obj, name, None) is None and field._obj is None:
#             field._obj = field.model_class()
#           if len(fielddict[name])>0:
#             subfields_to_populate = fielddict[name]
#         field.populate_obj(obj, name, subfields_to_populate)  
#       else:
#         field.populate_obj(obj, name) 

# class RacBaseForm(ModelForm, PartialEditForm):
#   pass # double inheritance from ModelForm and our special populate_obj

class ArticleBaseForm(RacBaseForm):
  def process(self, formdata=None, obj=None, **kwargs):
    super(ArticleBaseForm, self).process(formdata, obj, **kwargs)
    # remove all *article fields that don't match new type
    typedata = Article.type_data_name(self.data.get('type', 'default'))
    for embedded_type in EMBEDDED_TYPES:
      if embedded_type != typedata:
        del self._fields[embedded_type]

  def populate_obj(self, obj, fields_to_populate=None):
    if not type(obj) is Article:
      raise TypeError('ArticleBaseForm can only handle Article models')
    if 'type' in self.data:
      new_type = self.data['type']
      # Tell the Article we have changed type
      obj.change_type(new_type)
    super(ArticleBaseForm, self).populate_obj(obj)

class RacModelSelectField(ModelSelectField):
  # TODO quick fix to change queryset.get(id=...) to queryset.get(pk=...)
  # This is required to accept custom primary keys
  # https://github.com/MongoEngine/flask-mongoengine/issues/82
  def process_formdata(self, valuelist):
    if valuelist:
      if valuelist[0] == '__None':
        self.data = None
      else:
        if self.queryset is None:
          self.data = None
          return

        try:
          # clone() because of https://github.com/MongoEngine/mongoengine/issues/56
          obj = self.queryset.clone().get(pk=valuelist[0])
          self.data = obj
        except DoesNotExist:
          self.data = None

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

    form_class = model_form(field.document_type_obj, converter=RacModelConverter(), 
      base_class=OrigForm, field_args={})
    return f.FormField(form_class, **kwargs)

  @converts('ReferenceField')
  def conv_Reference(self, model, field, kwargs):
      kwargs['allow_blank'] = not field.required
      return RacModelSelectField(model=field.document_type, **kwargs)

  @converts('FileField')
  def conv_File(self, model, field, kwargs):
    # TODO add validators
#     FileRequired(),
 #       FileAllowed(['jpg', 'png'], 'Images only!')
    return f.FileField(**kwargs)

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


class Authorization:

  def __init__(self, is_authorized, message='', only_fields=None, error_code=403):
    self.is_authorized = is_authorized
    self.message = message
    self.error_code = error_code
    # Privleged means that this authorization would not apply to the public
    # or a normal user. E.g. a user can only edit their own profile (privilege),
    # or an admin can see other people's orders
    self.only_fields = only_fields
    if is_authorized:
      logger.debug("Authorized: %s" % message)
    else:
      logger.info("UNAUTHORIZED: %s" % message)

  def is_privileged(self):
    return (self.error_code == 403 and self.is_authorized)

  def __nonzero__(self):
    return self.is_authorized

# Checks if user is logged in and authorized
class ResourceAccessPolicy(object):
  model_class = None
  levels = ['public', 'user', 'private', 'admin']
  
  def __init__(self, ops_levels=None, get_owner_func=None):
    if not ops_levels:
      self.ops_levels = {
        'view': 'public',
        'list': 'public',
        '_default': 'admin'
      }
    else:
      self.ops_levels = ops_levels
    if not get_owner_func:
      self.get_owner_func = lambda x: getattr(x, 'user', None)
    else:
      self.get_owner_func = get_owner_func

  def authorize(self, op, instance=None):
    if op not in self.ops_levels:
      level = self.ops_levels['_default']
    else:
      level = self.ops_levels[op]
    msg = '%s requires a logged in user' % op
    if level=='public':
      return Authorization(True,'%s is a publicly allowed operation' % op)
    elif level=='user':
      if g.user:
        return Authorization(True, msg)
      else:
        return Authorization(False, msg, error_code=401) # Denoted that the user should log in first
    elif level=='private':
      if not instance:
        return Authorization(False, 'Error: Cannot apply private access without an instance')
      instance_owner = self.get_owner_func(instance)
      
      if g.user and g.user.admin:
        return Authorization(True, '%s have access to do private operation %s on instance %s' % (unicode(instance_owner), op, instance))

      if not instance_owner:
        return Authorization(False, 'Error: Cannot identify user (field %s) which instance %s belongs to' % (unicode(self.user_field), instance))
      elif not g.user:
        return Authorization(False, msg, error_code=401) # Denotes that the user should log in first
      elif not g.user == instance_owner:
        return Authorization(False, '%s is a private operation which requires the owner to be logged in' % op)
      else:
        return Authorization(True, '%s have access to do private operation %s on instance %s' % (unicode(instance_owner), op, instance))
    elif level=='admin':
      if not g.user:
        return Authorization(False, msg, error_code=401) # Denotes that the user should log in first
      elif not g.user.admin:
        return Authorization(False, 'Need to be logged in with admin access')
      elif g.user:
        return Authorization(True, '%s is an admin' % unicode(g.user))
    return Authorization(False, 'error', 'This is catch all denied authorization, should not be here')

class ResourceRoutingStrategy:
  def __init__(self, model_class, plural_name, id_field='id', form_class=None, 
    parent_strategy=None, parent_reference_field=None, short_url=False, 
    list_filters=None, use_subdomain=False, access_policy=None):
    if use_subdomain and parent_strategy:
      raise ValueError("A subdomain-identified resource cannot have parents")
    self.form_class = form_class if form_class else model_form(model_class, base_class=RacBaseForm, converter=RacModelConverter())
    self.model_class = model_class
    self.resource_name = model_class.__name__.lower().split('.')[-1]  # class name, ignoring package name
    self.plural_name = plural_name
    self.parent = parent_strategy
    self.id_field = id_field
    self.use_subdomain = use_subdomain
    self.subdomain_part = None
    if self.use_subdomain:
      self.subdomain_part = '<' + self.resource_name + '>'
    elif self.parent:
      p = self
      while (p.parent and not p.use_subdomain):
        p = p.parent
      if p:
        self.subdomain_part = p.subdomain_part
    self.short_url = short_url
    self.fieldnames = [n for n in self.form_class.__dict__.keys() if (not n.startswith('_') and n is not 'model_class')]
    self.default_list_filters = list_filters
    # The field name pointing to a parent resource for this resource, e.g. article.world
    self.parent_reference_field = self.parent.resource_name if (self.parent and not parent_reference_field) else None
    self.access = access_policy if access_policy else ResourceAccessPolicy()
    self.access.model_class = self.model_class

  def get_url_path(self, part, op=None):
    parent_url = ('/' if (self.parent is None) else self.parent.url_item(None))
    op_val = op if op else ''
    # print "For %s we add %s %s %s" % (self.resource_name, parent_url, part, op_val)
    url = parent_url + part + ('/' if part else '') + op_val
    return url

  def url_list(self, op=None):
    return self.get_url_path(self.plural_name, op)

  def url_item(self, op=None):
    if self.use_subdomain:
      return self.get_url_path('', op)
    elif self.short_url:
      return self.get_url_path('<' + self.resource_name + '>', op)
    else:
      return self.get_url_path(self.plural_name + '/<' + self.resource_name + '>', op)

  def item_template(self):
    return '%s_item.html' % self.resource_name

  def list_template(self):
    return '%s_list.html' % self.resource_name

  def query_item(self, **kwargs):
    item_id = kwargs[self.resource_name]
    if objid_matcher.match(item_id):
      return self.model_class.objects.get(id=item_id)
    else:
      return self.model_class.objects.get(**{self.id_field: item_id})

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
    if self.default_list_filters:
      qr = self.default_list_filters(qr)
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

  def authorize(self, op, instance=None):
    return self.access.authorize(op, instance)


class ResourceError(Exception):

  default_messages = {
    400: u"%s" % _("Bad request or invalid input"),
    401: u"%s" % _("Unathorized access, please login"),
    403: u"%s" % _("Forbidden, this is not an allowed operation"),
    404: u"%s" % _("Resource not found"),
    500: u"%s" % _("Internal server error")
  }

  def __init__(self, status_code, r=None, message=None, form=None):
    message = message if message else self.default_messages.get(status_code, _('Unknown error'))
    if status_code == 400:
      form = r.get('form', None) if r else form
      if form:
        message = u"Bad request, invalid fields: %s" % form.errors
    Exception.__init__(self, "%i: %s" % (status_code, message))
    self.status_code = status_code
    self.message = message
    self.r = r

    logger.warning("%d: %s", self.status_code, self.message)

class ResourceHandler(View):
  allowed_ops = ['view', 'form_new', 'form_edit', 'list', 'new', 'replace', 'edit', 'delete']
  ignored_methods = ['as_view', 'dispatch_request', 'register_urls']
  get_post_pairs = {'edit':'form_edit', 'new':'form_new','replace':'form_edit', 'delete':'edit'}

  def __init__(self, strategy):
    self.logger = current_app.logger
    self.form_class = strategy.form_class
    self.strategy = strategy

  @classmethod
  def methods(cls, resource_methods):
    def real_decorator(func):
      func.resource_methods = resource_methods
      return func
    return real_decorator

  @classmethod
  def register_urls(cls, app, st, sub=False):
    # We try to parse out any methods added to this handler class, which we will use as separate endpoints
    custom_ops = []
    for name, m in inspect.getmembers(cls, predicate=inspect.ismethod):
      if (not name.startswith("_")) and (not name in cls.ignored_methods) and (not name in cls.allowed_ops):
        app.add_url_rule(st.get_url_path(name), 
          subdomain=st.parent.subdomain_part if st.parent else None, 
          methods=m.resource_methods if hasattr(m,'resource_methods') else ['GET'], 
          view_func=cls.as_view(st.endpoint_name(name), st))
        custom_ops.append(name)
    cls.allowed_ops.extend(custom_ops)
    logger.debug("Creating resource with url pattern %s and custom ops %s", st.url_item(), [st.get_url_path(o) for o in custom_ops])

    app.add_url_rule(st.url_item(), subdomain=st.subdomain_part, methods=['GET'], view_func=cls.as_view(st.endpoint_name('view'), st))
    app.add_url_rule(st.url_list('new'), subdomain=st.parent.subdomain_part if st.parent else None, methods=['GET'], view_func=cls.as_view(st.endpoint_name('form_new'), st))
    app.add_url_rule(st.url_item('edit'), subdomain=st.subdomain_part, methods=['GET'], view_func=cls.as_view(st.endpoint_name('form_edit'), st))
    app.add_url_rule(st.url_list(), subdomain=st.parent.subdomain_part if st.parent else None, methods=['GET'], view_func=cls.as_view(st.endpoint_name('list'), st))
    app.add_url_rule(st.url_list(), subdomain=st.parent.subdomain_part if st.parent else None, methods=['POST'], view_func=cls.as_view(st.endpoint_name('new'), st))
    app.add_url_rule(st.url_item(), subdomain=st.subdomain_part, methods=['PUT', 'POST'], view_func=cls.as_view(st.endpoint_name('replace'), st))
    app.add_url_rule(st.url_item(), subdomain=st.subdomain_part, methods=['PATCH', 'POST'], view_func=cls.as_view(st.endpoint_name('edit'), st))
    app.add_url_rule(st.url_item(), subdomain=st.subdomain_part, methods=['DELETE', 'POST'], view_func=cls.as_view(st.endpoint_name('delete'), st))
    
    if current_app:
      current_app.access_policy[st.resource_name] = st.access

    # print "in register url %s" % app.app
    # /<resource>/[_,view,edit] -> GET:fablr.co/helmgast/, GET:fablr.co/helmgast/view, GET|POST:fablr.co/helmgast/edit
    # /resource/[list,new] -> GET:/world/list, GET:/world/new
    # <resource>.host/[_,view,edit] -> -> GET:helmgast.fablr.co, GET:helmgast.fablr.co/view, GET|POST:helmgast.fablr.co/edit

    # [GET]<world>.<host>/[_,edit]          -> world_view, world_form_edit
    # [GET]<host>/world/[worlds,new]      -> world_list, world_form_new
    # [GET]<world>.<host>/<article>   -> article_view
    # [GET]<world>.<host>/articles


  def dispatch_request(self, *args, **kwargs):
    # If op is given by argument, we use that, otherwise we take it from endpoint
    # The reason is that endpoints are not unique, e.g. for a given URL there may be many endpoints
    # TODO unsafe to let us call a custom methods based on request args!
    r = self._parse_url(**kwargs)
    try:
      if r['op'] not in self.__class__.allowed_ops:
        raise ResourceError(400, "Attempted op %s is not allowed for this handler" % r['op'])
      r = self._query_url_components(r, **kwargs)
      r = getattr(self, r['op'])(r)  # picks the right method from the class and calls it!
    except ResourceError as err:
      if request.args.has_key('debug') and current_app.debug:
        raise # send onward if we are debugging
      if err.status_code == 400: # bad request
        if r['op'] in self.get_post_pairs:
          # we were posting a form
          r['op'] = self.get_post_pairs[r['op']] # change the effective op
          r['template'] = self.strategy.item_template()
          r[self.strategy.resource_name + '_form'] = r['form']

        # if json, return json instead of render
        if r['out'] == 'json':
          return self._return_json(r, err)
        elif 'template' in r:
          flash(err.message,'warning')
          return render_template(r['template'], **r), 400
        else:
          return err.message, 400

      elif err.status_code == 401: # unauthorized
        if r['out'] == 'json':
          return self._return_json(r, err)
        else:
          flash(err.message,'warning')
          # if fragment/json, just return 401
          return redirect(url_for('auth.login', next=request.path))

      elif err.status_code == 403: # forbidden
        # r['op'] = self.get_post_pairs[r['op']] if r['op'] in self.get_post_pairs else r['op']  # change the effective op
        # r['template'] = self.strategy.item_template()
        if r['out'] == 'json':
          return self._return_json(r, err)
        # elif 'template' in r:
        #   flash(err.message,'warning')
        #   return render_template(r['template'], **r), 403
        else:
          return err.message, 403

      elif err.status_code == 404:
        abort(404) # TODO, nicer 404 page?

      elif r['out'] == 'json':
        return self._return_json(r, err)
      else:
        raise  # Send the error onward, will be picked up by debugger if in debug mode
    except DoesNotExist:
      abort(404)
    except ValidationError as err:
      logger.exception("Validation error")
      resErr = ResourceError(400, message=err.message)
      if r['out'] == 'json':
        return self._return_json(r, resErr) 
      else:
        # Send the error onward, will be picked up by debugger if in debug mode
        # 3rd args is the current traceback, as we have created a new exception
        raise resErr, None, sys.exc_info()[2]
    except NotUniqueError as err:
      resErr = ResourceError(400, message=err.message)
      if r['out'] == 'json':
        return self._return_json(r, resErr)
      else:
        # Send the error onward, will be picked up by debugger if in debug mode
        # 3rd args is the current traceback, as we have created a new exception
        raise resErr, None, sys.exc_info()[2]
    except Exception as err:
      if r['out'] == 'json':
        return self._return_json(r, err, 500)
      else:
        logger.exception(err)
        raise  # Send the error onward, will be picked up by debugger if in debug mode

    # no error, render output
    if r['out'] == 'json':
      return self._return_json(r)
    elif 'next' in r:
      return redirect(r['next'])
    elif 'response' in r:
      return r['response'] # op function may have rendered the answer itself
    else:
      # if json, return json instead of render
      return render_template(r['template'], **r)

  def _return_json(self, r, err=None, status_code=0):
    if err:
      logger.exception(err)
      return jsonify({'error':err.__class__.__name__,'message':err.message, 'status_code':status_code}), status_code or err.status_code
    else:
      d = {k:v for k,v in r.iteritems() if k in ['item','list','op','parents','next', 'pagination']}
      return jsonify(d)

  def _parse_url(self, **kwargs):
    r = {'url_args':kwargs}
    op = request.args.get('op', request.endpoint.split('.')[-1].split('_',1)[-1]).lower()
    if op in ['form_edit', 'form_new', 'list']:
      # TODO faster, more pythonic way of getting intersection of fieldnames and args
      vals = {}
      for arg in request.args:
        if arg in self.strategy.fieldnames:
          val = request.args.get(arg).strip()
          if val:
            vals[arg] = val
      r['filter' if op is 'list' else 'prefill'] = vals
    r['op'] = op
    r['out'] = parse_out_arg(request.args.get('out',None)) # defaults to None, meaning _page.html
    r['parent_template'] = r['out'] # TODO, we only need one of out and parent_template
    if 'next' in request.args:
      r['next'] = request.args['next']
    return r

  def _query_url_components(self, r, **kwargs):
    if self.strategy.resource_name in kwargs:
      r['item'] = self.strategy.query_item(**kwargs)
      r[self.strategy.resource_name] = r['item']
    r['parents'] = self.strategy.query_parents(**kwargs)
    r.update(r['parents'])
    # print "url comps %s, r %s" % (kwargs, r)
    return r

  def view(self, r):
    item = r['item']
    auth = self.strategy.authorize(r['op'], item)
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r, message=auth.message)
    
    r['template'] = self.strategy.item_template()
    return r

  def form_edit(self, r):
    item = r['item']
    
    auth = self.strategy.authorize(r['op'], item)
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r, message=auth.message)

    form = self.form_class(obj=item, **r.get('prefill',{}))
    form.action_url = url_for('.' + self.strategy.endpoint_name('edit'), op='edit', **r['url_args'])
    r[self.strategy.resource_name + '_form'] = form
    r['op'] = 'edit' # form_edit is not used in templates...
    r['template'] = self.strategy.item_template()
    return r

  def form_new(self, r):
    auth = self.strategy.authorize(r['op'])
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r, message=auth.message)
    
    form = self.form_class(request.args, obj=None, **r.get('prefill',{}))
    form.action_url = url_for('.' + self.strategy.endpoint_name('new'), **r['url_args'])
    r[self.strategy.resource_name + '_form'] = form
    r['op'] = 'new' # form_new is not used in templates...
    r['template'] = self.strategy.item_template()
    return r

  def list(self, r):
    auth = self.strategy.authorize(r['op'])
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r, message=auth.message)
    
    listquery = self.strategy.query_list(request.args).filter(**r.get('filter',{}))
    if r.get('parents'):
      # TODO if the name of the parent resource is different than the reference field name 
      # it will not work
      listquery = listquery.filter(**r['parents'])
    page = request.args.get('page', 1)
    if page=='all':
      r['list'] = listquery
      r[self.strategy.plural_name] = listquery
    else:
      r['pagination'] = listquery.paginate(page=int(page), per_page=10)
      r['list'] = r['pagination'].items
      r[self.strategy.plural_name] = r['list']
    r['url_for_args'] = request.view_args
    r['url_for_args'].update(request.args.to_dict())
    r['template'] = self.strategy.list_template()
    return r

  def new(self, r):
    auth = self.strategy.authorize(r['op'])
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r, message=auth.message)

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

  def edit(self, r):
    item = r['item']
    auth = self.strategy.authorize(r['op'], item)
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r, message=auth.message)

    form = self.form_class(request.form, obj=item)
    logger.warning('Form %s validates to %s' % (request.form, form.validate()))
    if not form.validate():
      r['form'] = form
      raise ResourceError(400, r)
    if not isinstance(form, RacBaseForm):
      raise ValueError("Edit op requires a form that supports populate_obj(obj, fields_to_populate)")
    form.populate_obj(item, request.form.keys())
    item.save()
    # In case slug has changed, query the new value before redirecting!
    if not 'next' in r:
      r['next'] = url_for('.' + self.strategy.endpoint_name('view'), **self.strategy.all_view_args(item))
    logger.info("Edit on %s/%s", self.strategy.resource_name, item[self.strategy.id_field])
    return r

  def replace(self, r):
    item = r['item']
    auth = self.strategy.authorize(r['op'], item)
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r, message=auth.message)

    form = self.form_class(request.form, obj=item)
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
    auth = self.strategy.authorize(r['op'], item)
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r, message=auth.message)

    if not 'next' in r:
      if 'parents' in r:
        r['next'] = url_for('.' + self.strategy.endpoint_name('list'), **self.strategy.parent.all_view_args(getattr(item, self.strategy.parent_reference_field)))
      else:
        r['next'] = url_for('.' + self.strategy.endpoint_name('list'))
    self.strategy.authorize(r['op'], item)
    logger.info("Delete on %s with id %s", self.strategy.resource_name, item.id)
    item.delete()
    return r

