"""
  fablr.resource
  ~~~~~~~~~~~~~~~~

  An internal library for generating REST-like URL routes and request
  handling functionality for most of Fablr's models. This provides
  DRYness of code and simplified addition of new models.

  :copyright: (c) 2014 by Helmgast AB
"""

import inspect
import logging
import pprint
import re
import sys

import flask
from flask import request, render_template, flash, url_for, abort, g, current_app
from flask_babel import lazy_gettext as _
from flask_classy import FlaskView
from flask_mongoengine import Pagination
from flask_mongoengine.wtf import model_form
from flask_mongoengine.wtf.fields import ModelSelectField, NoneStringField, ModelSelectMultipleField, JSONField
from flask_mongoengine.wtf.models import ModelForm
from flask_mongoengine.wtf.orm import ModelConverter, converts
from flask import Response
from flask.json import jsonify
from flask.views import View
from mongoengine import ReferenceField, DateTimeField, Q, OperationError
from mongoengine.errors import DoesNotExist, ValidationError, NotUniqueError
from mongoengine.queryset.visitor import QNode
from werkzeug.datastructures import CombinedMultiDict, MultiDict
from werkzeug.exceptions import HTTPException
from wtforms import Form as OrigForm, StringField, SelectMultipleField
from wtforms import fields as f, validators as v, widgets
from wtforms.compat import iteritems, text_type
from wtforms.utils import unset_value
from wtforms.widgets import html5, HTMLString, html_params

from fablr.extensions import configured_locales
from fablr.model.misc import METHODS, safe_next_url
from fablr.model.world import EMBEDDED_TYPES, Article

logger = current_app.logger if current_app else logging.getLogger(__name__)

objid_matcher = re.compile(r'^[0-9a-fA-F]{24}$')


def generate_flash(action, name, model_identifiers, dest=''):
    # s = u'%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1
    #   else '', ', '.join(model_identifiers), u' to %s' % dest if dest else '')
    s = _('%(name)s was %(action)s', action=action, name=name)
    flash(s, 'success')
    return s

mime_types = {
    'html': 'text/html',
    'json': 'application/json',
    'csv': 'text/csv'
}

# import collections
#
# def flatten(d, parent_key='', sep='__'):
#     items = []
#     for k, v in d.items():
#         if v: # we ignore empty values, we don't want to use them
#             new_key = parent_key + sep + k if parent_key else k
#             if isinstance(v, collections.MutableMapping):
#                 items.extend(flatten(v, new_key, sep=sep).items())
#             else:
#                 items.append((new_key, v))
#     return dict(items)


# class BaseArgs(OrigForm):
#     debug = f.BooleanField() # if debug config is on, use this to show extra debug output
#     as_user = f.StringField() # if user is admin, show page as viewed by given username
#     # out = {modal, fragment, html}
#
# # Parse args
# class EditArgs(BaseArgs):
#     # method={PUT, PATCH, DELETE} to use instead of POST from a browser
#     method = f.StringField(validators=[v.AnyOf(['PUT', 'PATCH', 'DELETE'])])
#
#     # next={url} next URL to redirect to after completed POST, PUT, PATCH, DELETE, must be an URL within this website
#     next = f.StringField(validators=v.Regexp(r'^[/?].+')) # match relative urls only for time being
#
# # For GET item
# class GetArgs(BaseArgs):
#     # action={PUT, PATCH, DELETE} intended next action, e.g. to serve a form
#     action = f.StringField(validators=[v.AnyOf(['PUT', 'patch', 'DELETE'])])
#
#     # view={card, table}, type of view of a list, also view={markdown} on articles
#     view = f.StringField(validators=[v.AnyOf(['markdown'])])
#
#     # set prefill fields based on model form
#
#
# # For GET list
# class ListArgs(BaseArgs):
#     # page={1+, default 1}, which page we want to load in a list
#     page = f.IntegerField(validators=[v.NumberRange(1)], default=1)
#
#     # per_page={1+, default 20}, how many items per page of a list
#     per_page = f.IntegerField(validators=[v.NumberRange(-1)], default=20) # -1 means no limit
#
#     # order_by={key}, order a list by given key.
#       If prefixed with - or +, interpret as descending and ascending. Ascending default.
#     # order_by = StringField() # improve to support multiple order_by fields
#
#     # {key}={value}, interpret as a filter for LIST/INDEX views. Only existing, and allowed, fields.
#     # {key} can in turn have the form key__operator or key__subkey, key__subkey__operator
#     # e.g. title__lte or author__name__exists
#     # valid suffixes:
#     # ne, lt, lte, gt, in, nin, mod, all, size, exists, exact, iexact, contains,
#     # icontains, istartswith, endswith, iendswith, match
#     # not__ before all above
#
#     # view={card, table}, type of view of a list, also view={markdown} on articles
#     view = f.StringField(v.AnyOf(['card', 'table']), default='table')
#
#     # q=, free text search this list
#     q = f.StringField()

# def model_args(baseform, model_class, field_names=None):
#     """Builds a form to parse args for a specific model class"""
#     arg_fields = OrderedDict()
#     if field_names:
#         ordering_choices = [u''] # allow empty choice, reduces validation errors
#         for name in field_names:
#             ordering_choices.extend(['+'+name,'-'+name, name])
#         arg_fields['order_by'] = f.StringField(validators=[v.AnyOf(ordering_choices)])
#         key_form = model_form(
#             model_class,
#             base_class=OrigForm,
#             only=field_names,
#             converter=RacModelConverter()
#             )
#         for name in field_names:
#             # Remove all defaults from the model, as they wont be useful for
#             # filtering or prefilling
#             getattr(key_form, name).kwargs.pop('default')
#         arg_fields['queryargs'] = f.FormField(key_form, separator='__')
#     return type(model_class.__name__ + 'Args', (baseform,), arg_fields)

common_args = frozenset(['page', 'per_page', 'debug', 'as_user', 'view', 'q', 'action', 'method', 'next', 'order_by'])

re_operators = re.compile(
    r'__(ne|lt|lte|gt|gte|in|nin|mod|all|size|exists|exact|iexact|contains|'
    'icontains|istartswith|endswith|iendswith|match|not__ne|not__lt|not__lte|'
    'not__gt|not__in|not__nin|not__mod|not__all|not__size|not__exists|'
    'not__exact|not__iexact|not__contains|not__icontains|not__istartswith|'
    'not__endswith|not__iendswith)$')
re_order_by = re.compile(r'^[+-]')


def prefillable_fields_parser(fields=None, **kwargs):
    fields = frozenset(fields or [])
    extend = {'fields': fields}
    extend.update(kwargs)
    return dict(ItemResponse.arg_parser, **extend)


def filterable_fields_parser(fields=None, **kwargs):
    fields = frozenset(fields or [])
    extend = {'order_by': lambda x: [y for y in x.lower().split(',') if re_order_by.sub('', y) in fields], 'fields': fields}
    extend.update(kwargs)
    return dict(ListResponse.arg_parser, **extend)


action_strings = {
    'post': 'posted',
    'put': 'put',
    'patch': 'patched',
    'delete': 'deleted'
}
action_strings_translated = {
    'post': _('posted'),
    'put': _('put'),
    'delete': _('deleted'),
    'patch': _('patched'),
}
instance_types_translated = {
    'article': _('The article'),
    'world': _('The world'),
    'publisher': _('The publisher'),
    'user': _('The user'),
}


def get_root_template(out_value):
    if out_value == 'modal':
        return current_app.jinja_env.get_or_select_template('_modal.html')
    elif out_value == 'fragment':
        return current_app.jinja_env.get_or_select_template('_fragment.html')
    else:
        return current_app.jinja_env.get_or_select_template('_page.html')


class ResourceResponse(Response):
    arg_parser = {
        # none should remain for subsequent requests
        'debug': lambda x: x.lower() == 'true',
        'as_user': lambda x: x,
        'render': lambda x: x if x in ['json', 'html'] else None,
        'out': lambda x: x if x in ['modal', 'fragment'] else None,
        'locale': lambda x: x if x in configured_locales else None,
        'intent': lambda x: x if x.upper() in METHODS else None,
    }

    def __init__(self, resource_view, queries, method, formats=None, extra_args=None):
        # Can be set from Model
        assert resource_view
        self.resource_view = resource_view

        self.resource_queries = []
        assert queries and isinstance(queries, list)
        for q in queries:
            assert isinstance(q, tuple)
            assert isinstance(q[0], basestring)
            setattr(self, q[0], q[1])
            self.resource_queries.append(q[0])  # remember names in order

        self.method = method
        self.access = resource_view.access_policy
        self.model = resource_view.model

        # To be set from from route
        self.formats = formats or frozenset(['html', 'json'])
        self.args = self.parse_args(self.arg_parser, extra_args or {})
        super(ResourceResponse, self).__init__()  # init a blank flask Response

    def auth_or_abort(self, instance=None):
        instance = instance or getattr(self, 'instance', None)
        auth = self.access.authorize(self.method, instance=instance)
        if auth:
            # if there's an intent, we also need to check that it's allowed
            intent = self.args.get('intent', None)
            if intent:
                auth = self.access.authorize(intent, instance=instance)
        if not auth:
            abort(auth.error_code, auth.message)
        else:
            self.auth = auth

    def render(self):
        if self.args['render']:
            best_type = mime_types[self.args['render']]
        else:
            best_type = request.accept_mimetypes.best_match([mime_types[m] for m in self.formats])
        if best_type == 'text/html':
            template_args = vars(self)  # All local and inherited variables
            template_args['root_template'] = get_root_template(self.args.get('out', None))
            self.set_data(render_template(self.template, **template_args))
            return self
        elif best_type == 'application/json':
            # TODO this will create a new response, which is a bit of waste
            # Need to at least keep the status from before
            if hasattr(self, 'form') and self.form and self.form.errors:
                return jsonify(errors=self.form.errors), self.status
            else:
                return jsonify({k: getattr(self, k) for k in self.json_fields}), self.status
        else:  # csv
            abort(406)  # Not acceptable content available

    def error_response(self, err, status=0):
        general_errors = []
        if isinstance(err, NotUniqueError):
            if 'title' in self.form:
                self.form['title'].errors.append('Duplicate title already exists, try renaming')
            elif 'slug' in self.form:
                self.form['slug'].errors.append('Duplicate slug already exists, try renaming')
            else:
                general_errors.append('Duplicate title already exists, try renaming')

        elif isinstance(err, ValidationError):
            # TODO checkout ValidationError._format_errors()
            for k, v in err.errors.items():
                msg = v.message if hasattr(v, 'message') and v.message else str(v)
                if k in self.form:  # We have a field, append the error there
                    errors = self.form[k].errors
                    if isinstance(errors, dict):
                        errors = v
                    else:
                        errors.append(msg)
                else:
                    general_errors.append(msg)
        else:
            general_errors.append(str(err))
        flash(_("Errors in form, %(errors)s", errors=u",".join(general_errors)), 'danger')
        return self, status or 400


    @staticmethod
    def parse_args(arg_parser, extra_args):
        """Parses request args through a form that sets defaults or removes invalid entries
        """
        args = {'fields': MultiDict()}  # ensure we always have a fields value
        # values for same URL param (e.g. key=val1&key=val2)
        # req_args = CombinedMultiDict([request.args, extra_args])
        req_args = request.args.copy()
        for k, v in extra_args.iteritems():
            req_args.add(k, v)
        # Iterate over arg_parser keys, so that we are guaranteed to have all default keys present
        for k in arg_parser:
            if k is not 'fields':
                # Defaults to empty string to ensure all keys exists
                args[k] = arg_parser[k](req_args.get(k, ''))
            else:
                fields = arg_parser[k]
                for q, w in req_args.iteritems(multi=True):
                    if q not in arg_parser:  # Means its a field name, not a pre-defined arg
                        # new_k = re_operators.sub('', q)  # remove mongo operators from filter key
                        new_k = q.split('__', 1)[0]  # allow all operators, just check field is valid
                        if new_k in fields:
                            args['fields'].add(q, w)
        # print args, arg_parser
        return args


class ListResponse(ResourceResponse):
    """index, listing of resources"""

    json_fields = frozenset(['query', 'pagination'])
    arg_parser = dict(ResourceResponse.arg_parser, **{
        'page': lambda x: int(x) if x.isdigit() and int(x) > 1 else 1,
        'per_page': lambda x: int(x) if x.lstrip('-').isdigit() and int(x) >= -1 else 15,
        'view': lambda x: x.lower() if x.lower() in ['card', 'table', 'list'] else None,
        'order_by': lambda x: '',
        'q': lambda x: x
    })
    method = 'list'

    def __init__(self, resource_view, queries, method='list', formats=None, extra_args=None):
        list_arg_parser = getattr(resource_view, 'list_arg_parser', None)
        if list_arg_parser:
            self.arg_parser = list_arg_parser
        super(ListResponse, self).__init__(resource_view, queries, method, formats, extra_args)
        self.template = resource_view.list_template

    @property  # For convenience
    def query(self):
        return getattr(self, self.resource_queries[0])  # first queried item is the query

    @query.setter
    def query(self, x):
        setattr(self, self.resource_queries[0], x)

    def slug_to_id(self, field, slug):
        if objid_matcher.match(slug):
            return slug  # Is already Object ID
        elif isinstance(field, ReferenceField):
            instance = field.document_type.objects(slug=slug).only('id').first()
            if instance:
                return instance.id
            else:
                return None
        else:
            return slug

    def render(self):
        self.paginate()
        return super(ListResponse, self).render()

    def prepare_query(self):  # also filter by authorization, paginate
        """Prepares an original query based on request args provided, such as
        ordering, filtering, pagination etc """
        if self.args['order_by']:  # is a list
            self.query = self.query.order_by(*self.args['order_by'])
        if self.args['fields']:
            built_query = None
            for k, values in self.args['fields'].iterlists():
                # Field name is string until first __ (operators are after)
                field = self.model._fields[k.split('__', 1)[0]]
                q = Q(**{k: self.slug_to_id(field, values[0])})
                if len(values) > 1:  # multiple values for this field, combine with or
                    for v in values[1:]:
                        q = q._combine(Q(**{k: self.slug_to_id(field, v)}), QNode.OR)
                if not built_query:
                    built_query = q
                else:
                    built_query = built_query._combine(q, QNode.AND)
            self.query = self.query.filter(built_query)
        if self.args['q']:
            # Doing this twice will throw error, but we cannot guarantee we won't runt prepare_query twice
            try:
                self.query = self.query.search_text(self.args['q']).order_by('$text_score')
            except OperationError:
                pass

        self.filter_options = {}
        for f in self.model._fields.keys():
            field = self.model._fields[f]
            if hasattr(field, 'filter_options'):
                self.filter_options[f] = field.filter_options(self.model)



    def paginate(self):
        # TODO max query size 10000 implied here
        per_page = self.args['per_page'] if self.args['per_page'] > 0 else 10000
        # TODO, this is a fix for an issue in MongoEngine https://github.com/MongoEngine/mongoengine/issues/1522
        try:
            self.pagination = Pagination(iterable=self.query, page=self.args['page'], per_page=per_page)
        except TypeError:  # Try again, as a race condition might stop first one
            self.pagination = Pagination(iterable=self.query, page=self.args['page'], per_page=per_page)
        self.query = self.pagination.items  # set default query as the paginated one


class ItemResponse(ResourceResponse):
    """both for getting and editing items of resources"""

    json_fields = frozenset(['instance'])
    arg_parser = dict(ResourceResponse.arg_parser, **{
        'view': lambda x: x.lower() if x.lower() in ['markdown', 'pay', 'cart', 'details'] else None,
        'next': lambda x: safe_next_url(x)
    })

    def __init__(self, resource_view, queries, method='get', formats=None, extra_args=None,
                 form_class=None, extra_form_args=None):
        item_arg_parser = getattr(resource_view, 'item_arg_parser', None)
        if item_arg_parser:
            self.arg_parser = item_arg_parser
        super(ItemResponse, self).__init__(resource_view, queries, method, formats, extra_args)

        self.template = resource_view.item_template

        if (self.method != 'get') or self.args['intent']:
            form_args = extra_form_args or {}
            if self.args['intent']:
                # we want to serve a form, pre-filled with field values and parent queries
                form_args.update({k: getattr(self, k) for k in self.resource_queries[1:]})
                form_args.update(self.args['fields'].iteritems())
                if self.args['intent'] == 'post':
                    # Will a post will not go to same URL, but a different on (e.g. a list
                    # endpoint without an id parameter
                    new_args = dict(request.view_args)
                    new_args.pop('id', None)
                    self.action_url = url_for(request.endpoint.replace(':get', ':post'), **new_args)
                else:
                    # Will take current endpoint (a get) and returns same url but with method from intent
                    self.action_url = url_for(request.endpoint, method=self.args['intent'], **request.view_args)
            form_class = form_class or self.resource_view.form_class
            self.form = form_class(formdata=request.form, obj=self.instance, **form_args)

    def validate(self):
        return self.form.validate()

    def commit(self, new_instance=None, flash=True):
        new_args = dict(request.view_args)
        new_args.pop('id', None)
        if self.method == 'delete':
            self.instance.delete()
        else:
            instance = new_instance or self.instance
            instance.save()
            self.instance = instance  # only save back to response if successful in case we have a post
        log_event(self.method, self.instance, flash=flash)

    @property  # For convenience
    def instance(self):
        return getattr(self, self.resource_queries[0])  # first queried item is the instance

    @instance.setter
    def instance(self, x):
        setattr(self, self.resource_queries[0], x)

    @property
    def form(self):
        return getattr(self, self.resource_queries[0] + "_form", None)  # first queried item is the instance

    @form.setter
    def form(self, x):
        setattr(self, self.resource_queries[0] + "_form", x)


def log_event(action, instance=None, message='', user=None, flash=True):
    # <datetime> <user> <action> <object> <message>
    # martin patch article(helmgast)
    # The article theArticle was patched
    # Artikeln theArticle aandrad
    user = user or g.user
    if user:
        user.log(action, instance, message)
    else:
        user = "System"
    logger.info("%s %s %s", user, action_strings[action], " (%s)" % message if message else "")
    if instance:
        name = instance_types_translated.get(instance._class_name.lower(), _('The item'))
    else:
        name = _('The item')
    # print name
    if flash:
        generate_flash(action_strings_translated[action], name, instance)


def parse_out_arg(out_param):
    if out_param == 'json':
        return out_param
    elif out_param in ['page', 'modal', 'fragment']:
        return '_%s.html' % out_param  # to use as template path
        # used in Jinja
    else:
        return None  # Same as page, but set as None in order to not override template given inheritance


class ResourceView(FlaskView):
    def after_request(self, name, response):
        """Makes sure all ResourceResponse objects are rendered before sending onwards"""
        if isinstance(response, ResourceResponse):
            return response.render()
        else:
            return response

    @classmethod
    def register_with_access(cls, app, domain):
        current_app.access_policy[domain] = cls.access_policy
        return cls.register(app)


def route_subdomain(app, rule, **options):
    # if not current_app.config.get('ALLOW_SUBDOMAINS', False) and 'subdomain' in options:
    #     sub = options.pop('subdomain')
    #     rule = "/sub_" + sub + "/" + rule.lstrip("/")
    return app.route(rule, **options)


# WTForm Basics to remember
# creating a form instance will have all data from formdata (input) take precedence. Not having it in
# formdata is same as setting it to 0 / default.
# to avoid a form field value to impact the object, remove it from the form. populate_obj can only
# take data from fields that exist in the form.
# when using a fieldlist or formfield we are just encapsulating forms that work as usual.

class RacBaseForm(ModelForm):
    # TODO if fields_to_populate are set to use form keys, a deleted field may mean
    # no form key is left in the submitted form, ignoring that delete
    def populate_obj(self, obj, fields_to_populate=None):
        if fields_to_populate:
            # FormFields in form args will have '-' do denote it's subfields. We
            # only want the first part, or it won't match the field names
            new_fields_to_populate = set([fld.split('__', 1)[0] for fld in fields_to_populate])
            # print "In populate, fields_to_populate before \n%s\nand after\n%s\n" % (
            #     fields_to_populate, new_fields_to_populate)
            newfields = [(name, fld) for (name, fld) in iteritems(self._fields) if name in new_fields_to_populate]
        else:
            newfields = iteritems(self._fields)
        for name, field in newfields:
            if isinstance(field, f.FormField) and getattr(obj, name, None) is None and field._obj is None:
                field._obj = field.model_class()  # new instance created
            if isinstance(field, f.FileField) and field.data == '':
                # Don't try to write empty FileField
                continue
            field.populate_obj(obj, name)


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
        super(ArticleBaseForm, self).populate_obj(obj, fields_to_populate)


class MultiCheckboxField(f.SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class TagField(SelectMultipleField):

    def __init__(self, queryset, **kwargs):
        self.queryset = queryset
        super(TagField, self).__init__(**kwargs)

    @classmethod
    def _remove_duplicates(cls, seq):
        """Remove duplicates in a case insensitive, but case preserving manner"""
        d = {}
        for item in seq:
            if item.lower() not in d:
                d[item.lower()] = True
                yield item

    def iter_choices(self):
        # Selects distinct values for the field tags in the queryset that represents all documents for this model
        for value in self.queryset.distinct('tags'):
            selected = self.data is not None and self.coerce(value) in self.data
            yield (value, value, selected)

    def pre_validate(self, form):
        pass  # Override parent class method which checks that every choice is in

    def process_formdata(self, valuelist):
        try:
            self.data = list(self._remove_duplicates(self.coerce(x) for x in valuelist))
            if len(self.data) == 0:
                self.data = None  # needed to actually clear the value in Mongoengine
        except ValueError:
            raise ValueError(self.gettext('Invalid choice(s): one or more data inputs could not be coerced'))

class SelectizeWidget(object):

    def __init__(self, html_tag='ul', prefix_label=True):
        self.html_tag = 'input type="text"'  # ignore
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.id)
        html_class = kwargs.get('class', '')
        kwargs['class'] = html_class + ' selectize'

        return HTMLString('<%s %s value="%s">' % (self.html_tag, html_params(**kwargs),
                                                  ', '.join([item.slug for item in field.data])))

class FablrModelSelectMultipleField(ModelSelectMultipleField):
    """
    A variant of ModelSelectMultipleField that keeps order of selected items between saves, which is otherwise thrown away.
    """

    def __init__(self, **kwargs):
        super(FablrModelSelectMultipleField, self).__init__(**kwargs)

    def iter_choices(self):
        if self.allow_blank:
            yield (u'__None', self.blank_text, self.data is None)

        if self.queryset is None:
            return

        self.queryset.rewind()
        if isinstance(self.data, list):
            selected = self.data
        elif self.data:
            selected = [self.data]
        else:
            selected = []

        for obj in selected:
            label = self.label_attr and getattr(obj, self.label_attr) or obj
            yield (obj.id, label, True)
        for obj in self.queryset:
            label = self.label_attr and getattr(obj, self.label_attr) or obj
            if obj not in selected:
                yield (obj.id, label, False)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                if not self.queryset:
                    self.data = None
                    return

                self.queryset.rewind()
                tmp = dict()
                for obj in self.queryset:
                    try:
                        i = valuelist.index(str(obj.id))
                        tmp[i] = obj
                    except ValueError:
                        pass
                self.data = [tmp[k] for k in sorted(tmp)]
                if not len(self.data):
                    self.data = None


class FablrModelSelectField(ModelSelectField):
    pass


class RacModelConverter(ModelConverter):
    @converts('EmbeddedDocumentField')
    def conv_EmbeddedDocument(self, model, field, kwargs):
        kwargs = {
            'validators': [],
            'filters': [],
            'default': field.default or field.document_type_obj,
            # Important. This separator makes the form also able to double as parser
            # for filter args to mongoengine, of type 'author__name'.
            'separator': '__'
        }
        # The only difference to normal ModelConverter is that we use the original,
        # insecure WTForms form base class instead of the CSRF enabled one from
        # flask-wtf. This is because we are in a FormField, and it doesn't require
        # additional CSRFs.

        form_class = model_form(field.document_type_obj, converter=RacModelConverter(),
                                base_class=OrigForm, field_args={})
        return f.FormField(form_class, **kwargs)

    @converts('ListField')
    def conv_List(self, model, field, kwargs):
        if field.name == 'tags':
            return TagField(queryset=model.objects(), **kwargs)
        elif isinstance(field.field, ReferenceField):
            kwargs[
                'allow_blank'] = not field.required  # Added line, to make reference fields inslide listfields to allow blanks
            return FablrModelSelectMultipleField(model=field.field.document_type, **kwargs)
        if field.field.choices:
            kwargs['multiple'] = True
            return self.convert(model, field.field, kwargs)
        field_args = kwargs.pop("field_args", {})
        unbound_field = self.convert(model, field.field, field_args)
        unacceptable = {
            'validators': [],
            'filters': [],
            'min_entries': kwargs.get('min_entries', 0)
        }
        kwargs.update(unacceptable)
        return f.FieldList(unbound_field, **kwargs)

    @converts('ReferenceField')
    def conv_Reference(self, model, field, kwargs):
        kwargs['allow_blank'] = not field.required
        return ModelSelectField(model=field.document_type, **kwargs)

    @converts('URLField')
    def conv_URL(self, model, field, kwargs):
        kwargs['validators'].append(v.URL())
        self._string_common(model, field, kwargs)
        kwargs.setdefault('widget', html5.URLInput())  # Set if not set from before
        return NoneStringField(**kwargs)

    @converts('EmailField')
    def conv_Email(self, model, field, kwargs):
        kwargs['validators'].append(v.Email())
        self._string_common(model, field, kwargs)
        kwargs.setdefault('widget', html5.EmailInput())  # Set if not set from before
        return NoneStringField(**kwargs)

    @converts('IntField')
    def conv_Int(self, model, field, kwargs):
        self._number_common(model, field, kwargs)
        kwargs.setdefault('widget', html5.NumberInput(step='1'))  # Set if not set from before
        return f.IntegerField(**kwargs)

    # Temporarily not used. datetime HTML5 inputs are in unclear support and cant handle seconds
    # @converts('DateTimeField')
    # def conv_DateTime(self, model, field, kwargs):
    #   kwargs.setdefault('widget', html5.DateTimeInput()) # Set if not set from before
    #   return f.DateTimeField(**kwargs)

    @converts('FileField')
    def conv_File(self, model, field, kwargs):
        # TODO add validators
        #     FileRequired(),
        #       FileAllowed(['jpg', 'png'], 'Images only!')
        return f.FileField(**kwargs)

    @converts('StringField')
    def conv_String(self, model, field, kwargs):
        if field.regex:
            kwargs['validators'].append(v.Regexp(regex=field.regex))
        self._string_common(model, field, kwargs)
        if 'password' in kwargs:
            if kwargs.pop('password'):
                return f.PasswordField(**kwargs)
        if field.max_length and field.max_length < 100:  # changed from original code
            return f.StringField(**kwargs)
        return f.TextAreaField(**kwargs)

    @converts('DynamicField')
    def conv_DynamicField(self, model, field, kwargs):
        return JSONField(**kwargs)


class ResourceError(Exception):
    default_messages = {
        400: u"%s" % _("Bad request or invalid input"),
        401: u"%s" % _("Unauthorized access, please login"),
        403: u"%s" % _("Forbidden, this is not an allowed operation"),
        404: u"%s" % _("Resource not found"),
        500: u"%s" % _("Internal server error")
    }

    def __init__(self, status_code, message=None, r=None, field_errors=None, template=None, template_vars=None):
        message = message if message else self.default_messages.get(status_code, u"%s" % _('Unknown error'))
        self.r = r
        if r:
            form = r.get('form', None)
            self.field_errors = form.errors if form else None
            self.template = r.get('template', None)
            self.template_vars = r
        if status_code == 400 and field_errors:
            message += u", invalid fields: \n%s" % pprint.pformat(field_errors)
        self.message = message
        self.status_code = status_code

        if field_errors:
            self.field_errors = field_errors
        if template:
            self.template = template
        if template_vars:
            self.template_vars = template_vars

        logger.warning(u"%d: %s%s", self.status_code, self.message,
                       u"\n%s\nin resource: \n%s\nwith formdata:\n%s" %
                       (request.url, pprint.pformat(self.r).decode('utf-8'), pprint.pformat(dict(request.form))))
        Exception.__init__(self, "%i: %s" % (status_code, message))


class Authorization:
    def __init__(self, is_authorized, message='', privileged=False, only_fields=None, error_code=403):
        self.is_authorized = is_authorized
        self.message = message
        self.error_code = error_code
        self.privileged = privileged
        # Privileged means that this authorization would not apply to the public
        # or a normal user. E.g. a user can only edit their own profile (privilege),
        # or an admin can see other people's orders
        self.only_fields = only_fields

    def __repr__(self):
        return u"%s%s" % (
            "Authorized" if self.is_authorized else "UNAUTHORIZED", u": %s" % self.message if self.message else "")

    def is_privileged(self):
        return self.privileged

    def __nonzero__(self):
        return self.is_authorized


# Checks if user is logged in and authorized
class ResourceAccessPolicy(object):
    model_class = None
    levels = ['public', 'user', 'reader', 'editor', 'owner', 'admin']
    translate = {'post': 'new', 'patch': 'edit', 'put': 'edit', 'index': 'list', 'delete': 'edit', 'get': 'view'}

    def __init__(self, ops_levels=None):
        if not ops_levels:
            self.ops_levels = {
                'view': 'public',
                'list': 'public',
                '_default': 'admin'
            }
        else:
            self.ops_levels = ops_levels

    def authorize(self, op, instance=None):
        if op in self.translate:  # TODO temporary translation between old and new op words, e.g. patch vs edit
            op = self.translate[op]
        if op not in self.ops_levels:
            level = self.ops_levels['_default']
        else:
            level = self.ops_levels[op]

        changed_level = self.get_access_level(op, instance)
        if changed_level:
            level = changed_level

        if level == 'public':
            return Authorization(True, _("%(op)s is a publicly allowed operation", op=op))
        elif level == 'user':
            return self.is_user(op, instance)  # if we have a user, doesnt matter if admin

        auth = self.is_user(op, instance)
        if not auth:
            return auth
        if level == 'reader':
            return (self.is_reader(op, instance) or
                    self.is_editor(op, instance) or
                    self.is_owner(op, instance) or
                    self.is_admin(op, instance))
        elif level == 'editor':
            return (
                self.is_editor(op, instance) or
                self.is_owner(op, instance) or
                self.is_admin(op, instance))
        elif level == 'owner':
            return (
                self.is_owner(op, instance) or
                self.is_admin(op, instance))
        elif level == 'admin':
            return self.is_admin(op, instance)
        return Authorization(False, _("This is catch all denied authorization, should not be here"))

    def auth_or_abort(self, response, instance=None):
        # if 'args' not in response or 'intent' not in response['args']:
        #     raise KeyError('Expects an intent arg, even if empty. Make sure to parse_args before auth')
        action = response['action']  # choose intent before action
        # print "Auth for %s, intent %s action %s" % (action, response['args']['intent'], response['action'])
        auth = self.authorize(action, instance)
        if not auth:
            raise ResourceError(auth.error_code, r={'TBD': 'TBD'}, message=auth.message)
        else:
            response['auth'] = auth
            return response

    def get_access_level(self, op, instance):
        return None

    def is_user(self, op, instance):
        msg = _("%(op)s requires a logged in user", op=op)
        if g.user:
            return Authorization(True, msg)
        else:
            return Authorization(False, msg, error_code=401)  # Denoted that the user should log in first

    def is_reader(self, op, instance):
        return Authorization(False, _("Undefined access status given for this instance"), error_code=401)

    def is_editor(self, op, instance):
        return Authorization(False, _("Undefined access status given for this instance"), error_code=401)

    def is_owner(self, op, instance):
        return Authorization(False, _("Undefined access status given for this instance"), error_code=401)

    def is_admin(self, op, instance):
        if g.user.admin:
            return Authorization(True, _("%(user)s is an admin", user=g.user), privileged=True)
        else:
            return Authorization(False, _("Need to be logged in with admin access"))


class DisabledField(StringField):
    """A disabled field assumes it has default data that should be displayed when rendered but will ignore
    input from forms"""

    def process(self, formdata, data=unset_value):
        # Ignore formdata input, otherwise proceed as normal
        if data == unset_value:
            raise ValueError("DisabledField needs to be explicitly set to a default value")
        self.flags.disabled = True
        super(StringField, self).process(None, data)