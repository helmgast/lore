"""
  lore.resource
  ~~~~~~~~~~~~~~~~

  An internal library for generating REST-like URL routes and request
  handling functionality for most of Lore's models. This provides
  DRYness of code and simplified addition of new models.

  :copyright: (c) 2014 by Helmgast AB
"""
import itertools
import logging
import math
from time import time
import pprint
import re
from tools.profiler_decorator import profile
import types
from itertools import chain
from typing import Dict, Sequence

from flask import Response, abort, current_app, flash, g, render_template, request, session, url_for
from flask.json import jsonify
from flask_babel import lazy_gettext as _
from flask_classy import FlaskView
from flask_mongoengine import Pagination
from flask_mongoengine.wtf import model_form
from flask_mongoengine.wtf.fields import JSONField, ModelSelectField, ModelSelectMultipleField, NoneStringField
from flask_mongoengine.wtf.models import ModelForm
from flask_mongoengine.wtf.orm import ModelConverter, converts
from jinja2 import TemplatesNotFound
from mongoengine import InvalidQueryError, OperationError, Q, ReferenceField
from mongoengine.errors import NotUniqueError, ValidationError
from mongoengine.queryset.visitor import QNode
from werkzeug.datastructures import MultiDict
from werkzeug.utils import secure_filename
from wtforms import Form as OrigForm
from wtforms import SelectMultipleField, StringField
from wtforms import fields as f
from wtforms import validators, widgets
from wtforms.fields.core import UnboundField
from wtforms.utils import unset_value
from wtforms.widgets import HTMLString, Select, html5, html_params
from wtforms.widgets.core import HiddenInput

from lore.model.misc import METHODS, extract, localized_field_labels, safe_next_url
from lore.model.world import EMBEDDED_TYPES, Article

logger = current_app.logger if current_app else logging.getLogger(__name__)

objid_matcher = re.compile(r"^[0-9a-fA-F]{24}$")


def generate_flash(action, name, model_identifiers, dest=""):
    # s = u'%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1
    #   else '', ', '.join(model_identifiers), u' to %s' % dest if dest else '')
    s = _("%(name)s was %(action)s", action=action, name=name)
    flash(s, "success")
    return s


def mark_time_since_request(text):
    if hasattr(g, "start"):
        print(text, int(round((time() - g.start) * 1000)))


mime_types = {"html": "text/html", "json": "application/json", "csv": "text/csv"}

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
#             converter=ImprovedModelConverter()
#             )
#         for name in field_names:
#             # Remove all defaults from the model, as they wont be useful for
#             # filtering or prefilling
#             getattr(key_form, name).kwargs.pop('default')
#         arg_fields['queryargs'] = f.FormField(key_form, separator='__')
#     return type(model_class.__name__ + 'Args', (baseform,), arg_fields)

common_args = frozenset(
    ["debug", "as_user", "render", "out", "intent", "view", "next", "q", "action", "method", "order_by"]
)

re_operators = re.compile(
    r"__(ne|lt|lte|gt|gte|in|nin|mod|all|size|exists|exact|iexact|contains|"
    "icontains|istartswith|endswith|iendswith|match|not__ne|not__lt|not__lte|"
    "not__gt|not__in|not__nin|not__mod|not__all|not__size|not__exists|"
    "not__exact|not__iexact|not__contains|not__icontains|not__istartswith|"
    "not__endswith|not__iendswith)$"
)


def prefillable_fields_parser(fields=None, **kwargs):
    fields = frozenset(fields or [])
    forbidden = fields & common_args
    if forbidden:
        msg = f"Cannot allow field names colliding with common args names: {forbidden}"
        current_app.logger.error(msg)
        exit(1)
    extend = {"fields": fields}
    extend.update(kwargs)
    return dict(ItemResponse.arg_parser, **extend)


def filterable_fields_parser(fields=None, **kwargs):
    # filterable_fields = frozenset([f.split(".", 1)[0] for f in fields] or [])
    filterable_fields = frozenset(fields or [])
    forbidden = filterable_fields & common_args
    if forbidden:
        raise Exception(f"Cannot allow field names colliding with common args names: {forbidden}")
    extend = {
        "order_by": lambda x: [y for y in x.lower().split(",") if y.lstrip("+-") in fields],
        "fields": filterable_fields,
    }
    extend.update(kwargs)
    return dict(ListResponse.arg_parser, **extend)


action_strings = {"post": "posted", "put": "put", "patch": "patched", "delete": "deleted"}
action_strings_translated = {
    "post": _("posted"),
    "put": _("put"),
    "delete": _("deleted"),
    "patch": _("modified"),
}
instance_types_translated = {
    "article": _("The article"),
    "world": _("The world"),
    "publisher": _("The publisher"),
    "user": _("The user"),
}


def get_root_template(out_value):
    if out_value == "modal":
        return current_app.jinja_env.get_or_select_template("_modal.html")
    elif out_value == "fragment":
        return current_app.jinja_env.get_or_select_template("_fragment.html")
    else:
        return current_app.jinja_env.get_or_select_template("_root.html")


def set_theme(obj, type, *paths):
    name = f"{type}_theme"
    if type and paths:
        # != 'None' as this string may mean None in Mongoengine
        templates = ["%s/index.html" % secure_filename(p) for p in paths if p and p != "None"]
        if templates:
            try:
                theme = current_app.jinja_env.select_template(templates)
                setattr(obj, name, theme)
                return theme
            except TemplatesNotFound as err:
                logger.warning(f"Can't find named themes {paths} at {templates}")
    setattr(obj, name, None)
    return None


class ResourceResponse(Response):
    arg_parser = {
        # none should remain for subsequent requests
        "debug": lambda x: x.lower() == "true",
        "as_user": lambda x: x,
        "render": lambda x: x if x in ["json", "html"] else None,
        "out": lambda x: x if x in ["modal", "fragment"] else None,
        "intent": lambda x: x if x.upper() in METHODS else None,
    }

    json_fields = frozenset([])

    def __init__(self, resource_view, queries, method, formats=None, extra_args=None):
        # Can be set from Model
        assert resource_view
        self.resource_view = resource_view

        self.resource_queries = []
        assert queries and isinstance(queries, list)
        for q in queries:
            assert isinstance(q, tuple)
            assert isinstance(q[0], str)
            setattr(self, q[0], q[1])
            self.resource_queries.append(q[0])  # remember names in order

        self.method = method
        self.access = resource_view.access_policy
        self.model = resource_view.model
        self.general_errors = []

        # To be set from from route
        self.formats = formats or ["html", "json"]
        self.args = self.parse_args(self.arg_parser, extra_args or {})
        self.auth = None
        super(ResourceResponse, self).__init__()  # init a blank flask Response

    def set_theme(self, type, *paths):
        # Check if we have a theme arg, it should overrule the current theme
        # (e.g. if an article, override article_theme but not others)
        # Has theme in args?
        if (
            len(self.resource_queries) > 0
            and self.resource_queries[0] == type
            and ("fields" in self.args and self.args["fields"].get("theme", None))
        ):
            paths += (self.args["fields"]["theme"],)
        theme = set_theme(self, type, *paths)
        setattr(g, f"{type}_theme", theme)

    def auth_or_abort(self, res=None):
        res = res or getattr(self, "instance", None)
        auth = self.access.authorize(self.method, res=res)
        # if auth and res:
        #     # if there's an intent and a resource, we also should check that it's an allowed operation
        #     intent = self.args.get('intent', None)
        #     if intent:
        #         auth = self.access.authorize(intent, res=res)
        if not auth:
            if g.user:
                logger.warn('User "{user}" unauthorized "{msg}"'.format(user=g.user, msg=auth.message))
            abort(auth.error_code, auth.message)
        else:
            self.auth = auth

    def get_template_args(self):
        rv = {}
        # This takes both instance and class variables, and order is important as instance variables overrides class
        for k, arg in chain(self.__class__.__dict__.items(), self.__dict__.items()):
            if not isinstance(arg, types.FunctionType) and not k.startswith("_"):
                rv[k] = arg
        return rv

    # @profile()
    def render(self):
        if not self.auth:
            abort(403, _("Authorization not performed"))
        if self.args["render"]:
            best_type = mime_types[self.args["render"]]
        else:
            best_type = request.accept_mimetypes.best_match([mime_types[m] for m in self.formats])
        if best_type == "text/html":
            template_args = self.get_template_args()
            template_args["root_template"] = get_root_template(self.args.get("out", None))
            mark_time_since_request("Before render")
            self.set_data(render_template(self.template, **template_args))
            mark_time_since_request("After render")
            return self
        elif best_type == "application/json":
            # TODO this will create a new response, which is a bit of waste
            # Need to at least keep the status from before
            # if self.errors:
            #     return jsonify(errors=self.errors), self.status
            # else:
            rv = {k: getattr(self, k) for k in self.json_fields}
            flashes = session.get("_flashes", [])
            if flashes:
                rv["errors"] = []
                for one_flash in flashes:
                    rv["errors"].append(one_flash[1])  # Message
                session["_flashes"] = []
            return jsonify(rv), self.status
        else:  # csv
            logger.warn(
                f"Unsupported mime type '{best_type}' for resource request '{request}' with 'Accept: {request.accept_mimetypes}'"
            )
            abort(406)  # Not acceptable content available

    def error_response(self, err=None, status=0):
        general_errors = []
        # TODO better parse errors and link to the correct form field, so that we can display errors
        # next to them. This should work even with EmbeddedDocuments or MapFields.
        if isinstance(err, NotUniqueError):
            # This error comes from PyMongo with only a text message denoting which field was not unique
            # We need to parse it to allocate it back to the right field
            found = False
            msg = str(err)
            for key in list(self.form._fields.keys()):
                # When we check title, also check if there was a fault with the slug, as slug
                # normally is what is not unique, but will not be in the form fields
                # This means we will highlight the title field when slug is not unique
                if key == "title" and "$slug" in msg or f"${key}" in msg:
                    self.form[key].errors.append(
                        _("This field needs to be unique and another resource already have this value")
                    )
                    found = True
                    break
            if not found:
                general_errors.append(msg)

        elif isinstance(err, ValidationError):
            set_form_fields_errors(err.errors, self.form, general_errors)
        elif err:
            general_errors.append(str(err))
        general_errors = ", ".join(general_errors) if general_errors else ""
        error_field_names = [
            str(self.form[f].label.text) if self.form[f].label else self.form[f].name.capitalize()
            for f in self.form.errors.keys()
        ]
        flash(_("Check errors in form") + f": {', '.join(error_field_names)}, {general_errors}", "danger")
        return self, status or 400

    @staticmethod
    def parse_args(arg_parser, extra_args):
        """Parses request args through a form that sets defaults or removes invalid entries
        """
        args = MultiDict({"fields": MultiDict()})  # ensure we always have a fields value
        # values for same URL param (e.g. key=val1&key=val2)
        # req_args = CombinedMultiDict([request.args, extra_args])
        req_args = request.args.copy()
        for k, v in extra_args.items():
            req_args.add(k, v)
        # Iterate over arg_parser keys, so that we are guaranteed to have all default keys present
        for k in arg_parser:
            if k != "fields":
                # Defaults to empty string to ensure all keys exists
                args[k] = arg_parser[k](req_args.get(k, ""))
            else:
                fields = arg_parser[k]
                for q, w in req_args.items(multi=True):
                    if q not in arg_parser:  # Means its a field name, not a pre-defined arg
                        # new_k = re_operators.sub('', q)  # remove mongo operators from filter key
                        new_k = q.split("__", 1)[0]  # allow all operators, just check field is valid
                        if new_k in fields:
                            args["fields"].add(q, w)
        # print args, arg_parser
        return args


def set_form_fields_errors(error_dict, form, general_errors=None, error_path=""):
    """Sets errors from dict on fields in a WTForm. If we can't find the field on the form, we let it be a general error.
    WARNING, this is highly specific to WTForm internal details, due to WTForm not implemented with external errors in mind.

    Args:
        error_dict (dict): a (possibly nested) dict with keys as field names and values as error strings
        form (any): typically a WTForms, but just need to have a dict like structure with an errors list.

    Returns:
        [type]: [description]
    """
    if general_errors is None:
        general_errors = []
    for k, v in error_dict.items():
        try:
            field = form[k]
        except Exception as e1:
            field = None

        if field:
            error_path += f"{field.label if field.label else field.name}/"
        else:
            error_path += f"{k}/"

        if isinstance(v, dict):
            # We need to go deeper for the error
            set_form_fields_errors(v, field if field is not None else form, general_errors, error_path)
        elif field and isinstance(field, f.Field):
            # A tuple as errors means no validation has been done yet, WTForm internal details
            if isinstance(field.errors, tuple):
                raise ValueError("Run validation() on the form before attempting to add errors to it")
            try:
                field.errors.append(str(v))
            except Exception as e2:
                general_errors.append(f"{error_path}: {v}")
        else:
            general_errors.append(f"{error_path}: {v}")
    return general_errors


# class FilterableField2:

#     key = ""
#     name = ""
#     description = ""

#     def apply_to_query(self, query):
#         # Applies query to filter_options
#         return query

#     def filter_options(self):
#         return [("value", "Display")]

# class SortableField:

#     key = ""
#     name = ""
#     description = ""

#     def parse_order_by(self):
#         pass

#     def apply_to_query(self, query):
#         return query


class ListResponse(ResourceResponse):
    """index, listing of resources"""

    arg_parser = dict(
        ResourceResponse.arg_parser,
        **{
            "page": lambda x: int(x) if x.isdigit() and int(x) > 1 else 1,
            "per_page": lambda x: int(x) if x.lstrip("-").isdigit() and int(x) >= -1 else 15,
            "random": lambda x: int(x) if x.isdigit() and int(x) > 0 else 0,
            "view": lambda x: x.lower() if x.lower() in ["card", "table", "list", "index"] else None,
            "order_by": lambda x: [],  # Will be replaced by fields using a filterable_arg_parser
            "q": lambda x: x,
        },
    )
    method = "list"
    pagination, filter_options = None, {}

    def __init__(self, resource_view, queries, method="list", formats=None, extra_args=None):
        list_arg_parser = getattr(resource_view, "list_arg_parser", None)
        if not list_arg_parser:
            filterable_fields = getattr(resource_view, "filterable_fields", None)
            if filterable_fields is not None:
                list_arg_parser = filterable_fields.list_arg_parser
                self.filterable_fields = filterable_fields
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
        if isinstance(slug, str) and objid_matcher.match(slug):
            return slug  # Is already Object ID
        elif isinstance(field, ReferenceField):
            try:
                instance = field.document_type.objects(slug=slug).only("id").first()
            except InvalidQueryError:
                instance = None
            if instance:
                return instance.id
            else:
                return None
        else:
            return slug

    # queryable fields
    # sortable?
    # filterable?

    def finalize_query(
        self, aggregation=None, paginate=True, select_related=True
    ):  # also filter by authorization, paginate
        """Prepares an original query based on request args provided, such as
        ordering, filtering, pagination etc """
        # mark_time_since_request("Before finalize")

        if aggregation is None:
            aggregation = []

        self.pagination = ResponsePagination(self)

        # Apply text search
        if self.args["q"]:
            self.query = self.query.search_text(self.args["q"])
            self.args["order_by"].append("$text_score")

        # Apply filters
        if self.args["fields"]:
            built_query = None
            for k, values in self.args["fields"].lists():
                # Field name is string until first __ (operators are after)
                # field = self.model._fields[k.split("__", 1)[0]]
                # if k.endswith("__size"):
                #     values = [int(v) for v in values]
                # q = Q(**{k: self.slug_to_id(field, values[0])})
                q = Q(**{k: values[0]})
                # if len(values) > 1:  # multiple values for this field, combine with or
                #     for v in values[1:]:
                #         q = q._combine(Q(**{k: self.slug_to_id(field, v)}), QNode.OR)
                # built_query = built_query._combine(q, QNode.AND) if built_query else q
                built_query = q

            self.query = self.query.filter(built_query)

        # Populate filter options, options may be reduced by current query
        for field in self.filterable_fields.filter_dict.keys():
            # Fields may be composite like field.subfield, which we don't support with filter options
            field = field.split(".", 1)[0]
            fieldObj = self.model._fields.get(field, None)
            if fieldObj and hasattr(fieldObj, "filter_options"):
                self.filter_options[field] = fieldObj.filter_options(self.query)

        # Filterable fields

        # Apply sort / order, overruling any previous
        if self.args["order_by"]:  # is a list
            sort_aggregation = []
            order_by = []
            for ob in self.args["order_by"]:
                parts = ob.split(".")
                if len(parts) > 1:
                    field = self.model._fields.get(parts[0].lstrip("-+"), None)
                    # Allow sort by reference fields by doing aggregation lookup on them for sorting
                    if isinstance(field, ReferenceField) and not field.dbref:
                        sort_aggregation.append(
                            {
                                "$lookup": {
                                    "from": field.document_type._get_collection_name(),
                                    "localField": field.name,
                                    "foreignField": "_id",
                                    "as": f"{field.name}_lookup",
                                }
                            }
                        )
                        order_by.append(
                            f"{'-' if ob.startswith('-') else ''}{field.name}_lookup.{'.'.join(parts[1:])}"
                        )
                        continue
                order_by.append(ob)
            if sort_aggregation:
                sort_aggregation.append({"$sort": dict(self.query._get_order_by(order_by))})
                if self.pagination:
                    # Best performance if we add the limit and skip here
                    self.pagination.apply_to_aggregation(sort_aggregation)

                sort_aggregation.append(
                    {"$unset": [dct["$lookup"]["as"] for dct in sort_aggregation if "$lookup" in dct]}
                )
                aggregation += sort_aggregation
            else:
                self.query = self.query.order_by(*self.args["order_by"])

        if self.args["random"] > 0:
            aggregation.append({"$sample": {"size": self.args["random"]}})

        self.query = self.pagination.apply_to_query(self.query)
        if aggregation:
            if self.query._query:
                aggregation.insert(0, {"$match": self.query._query})
            agg_results = self.query._collection.aggregate(aggregation, cursor={})
            # Note, turns query into a static list
            self.query = [self.model._from_son(a) for a in agg_results]
        elif select_related:
            self.query.select_related()


class ResponsePagination(Pagination):
    def __init__(self, r):

        per_page = int(r.args["per_page"])
        page = int(r.args["page"])
        if per_page < 0:
            per_page = 10000  # Max page size

        # TODO, a fix because pagination will otherwise reset any previous .limit() set on the query.
        # https://github.com/MongoEngine/flask-mongoengine/issues/310
        if getattr(r.query, "_limit", None):
            per_page = min(per_page, r.query._limit)
            page = min(page, math.ceil(r.query._limit // per_page))  # // is integer division

        if page < 1:
            abort(404)

        self.page = page
        self.per_page = per_page
        self.count = 0
        self.response = r
        self.skip = (page - 1) * per_page

    def apply_to_aggregation(self, pipeline):
        # Below comment from base.py in MongoEngine:
        #
        # As per MongoDB Documentation (https://docs.mongodb.com/manual/reference/operator/aggregation/limit/),
        # keeping limit stage right after sort stage is more efficient. But this leads to wrong set of documents
        # for a skip stage that might succeed these. So we need to maintain more documents in memory in such a
        # case (https://stackoverflow.com/a/24161461).
        if self.per_page and {"$limit": self.per_page + (self.skip or 0)} not in pipeline:
            pipeline.append({"$limit": self.per_page + (self.skip or 0)})
        if self.skip and {"$skip": self.skip} not in pipeline:
            pipeline.append({"$skip": self.skip})
        return pipeline

    def apply_to_query(self, query):
        self.count = query.count()
        return query.skip(self.skip).limit(self.per_page)

    @property
    def pages(self):
        """The total number of pages"""
        return int(math.ceil(self.count / float(self.per_page)))

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        This is how you could render such a pagination in the templates:

        .. sourcecode:: html+jinja

            {% macro render_pagination(pagination, endpoint) %}
              <div class=pagination>
              {%- for page in pagination.iter_pages() %}
                {% if page %}
                  {% if page != pagination.page %}
                    <a href="{{ url_for(endpoint, page=page) }}">{{ page }}</a>
                  {% else %}
                    <strong>{{ page }}</strong>
                  {% endif %}
                {% else %}
                  <span class=ellipsis>…</span>
                {% endif %}
              {%- endfor %}
              </div>
            {% endmacro %}
        """
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or num > self.pages - right_edge
                or (num >= self.page - left_current and num <= self.page + right_current)
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num
        if last != self.pages:
            yield None


class ItemResponse(ResourceResponse):
    """both for getting and editing items of resources"""

    json_fields = frozenset(["instance"])
    arg_parser = dict(
        ResourceResponse.arg_parser,
        **{
            "view": lambda x: x.lower() if x.lower() in ["markdown", "pay", "cart", "details"] else None,
            "next": lambda x: safe_next_url(x),
        },
    )

    def __init__(
        self,
        resource_view,
        queries,
        method="get",
        formats=None,
        extra_args=None,
        form_class=None,
        extra_form_args=None,
    ):
        item_arg_parser = getattr(resource_view, "item_arg_parser", None)
        if item_arg_parser:
            self.arg_parser = item_arg_parser
        super(ItemResponse, self).__init__(resource_view, queries, method, formats, extra_args)

        self.template = resource_view.item_template

        if (self.method != "get") or self.args["intent"]:
            form_args = extra_form_args or {}
            if self.args["intent"]:
                # we want to serve a form, pre-filled with field values and parent queries
                form_args.update({k: getattr(self, k) for k in self.resource_queries[1:]})
                form_args.update(self.args["fields"].items())
                action_args = MultiDict({k: v for k, v in self.args.items() if v and k not in ["fields", "intent"]})
                action_args.update(self.args["fields"])
                if self.args["intent"] == "post":
                    # A post will not go to same URL, but a different on (e.g. a list endpoint without an id parameter)
                    self.action_url = url_for(
                        request.endpoint.replace(":get", ":post"),
                        **{k: v for k, v in request.view_args.items() if k != "id"},
                        **action_args,
                    )
                else:
                    # Will take current endpoint (a get) and returns same url but with method from intent
                    self.action_url = url_for(
                        request.endpoint, method=self.args["intent"], **request.view_args, **action_args
                    )
            else:
                # Set intent to method if we are post/put/patch as it is used in template to decide
                self.args["intent"] = self.method
            form_class = form_class or self.resource_view.form_class
            self.form = form_class(formdata=request.form, obj=self.instance, **form_args)

    def validate(self):
        return self.form.validate()

    def commit(self, new_instance=None, flash=True):
        if not self.auth:
            abort(403, _("Authorization not performed"))
        new_args = dict(request.view_args)
        new_args.pop("id", None)
        if self.method == "delete":
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


def log_event(action, instance=None, message="", user=None, flash=True):
    # <datetime> <user> <action> <object> <message>
    # martin patch article(helmgast)
    # The article theArticle was patched
    # Artikeln theArticle aandrad
    user = user or g.user
    if user:
        user.log(action, instance, message)
    else:
        user = "System"
    logger.info("%s %s %s", user, action_strings.get(action, "unknown"), " (%s)" % message if message else "")
    if instance:
        name = instance_types_translated.get(instance._class_name.lower(), _("The item"))
    else:
        name = _("The item")
    # print name
    if flash:
        generate_flash(action_strings_translated[action], name, instance)


def parse_out_arg(out_param):
    if out_param == "json":
        return out_param
    elif out_param in ["page", "modal", "fragment"]:
        return "_%s.html" % out_param  # to use as template path
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

    # @classmethod
    # def set_prefillable_fields(cls, fields, **kwargs):


def route_subdomain(app, rule, **options):
    # if not current_app.config.get('ALLOW_SUBDOMAINS', False) and 'subdomain' in options:
    #     sub = options.pop('subdomain')
    #     rule = "/sub_" + sub + "/" + rule.lstrip("/")
    return app.route(rule, **options)


class FilterableFields(Dict):
    def __init__(self, model, fields, **kwargs):
        self.filter_dict = {}
        for field in fields:
            if isinstance(field, tuple):
                self.filter_dict[field[0]] = field[1]
            elif field in model._fields and hasattr(model._fields[field], "verbose_name"):
                self.filter_dict[field] = model._fields[field].verbose_name
            else:
                self.filter_dict[field] = field
        self.list_arg_parser = filterable_fields_parser(self.filter_dict.keys(), **kwargs)


# WTForm Basics to remember
# creating a form instance will have all data from formdata (input) take precedence. Not having it in
# formdata is same as setting it to 0 / default.
# to avoid a form field value to impact the object, remove it from the form. populate_obj can only
# take data from fields that exist in the form.
# when using a fieldlist or formfield we are just encapsulating forms that work as usual.


class ImprovedBaseForm(ModelForm):

    # TODO if fields_to_populate are set to use form keys, a deleted field may mean
    # no form key is left in the submitted form, ignoring that delete
    def populate_obj(self, obj, fields_to_populate=None):
        super(ImprovedBaseForm, self).populate_obj(obj)

    # field.populate_obj(obj, name)
    #     if fields_to_populate:
    #         # FormFields in form args will have '-' do denote it's subfields. We
    #         # only want the first part, or it won't match the field names
    #         new_fields_to_populate = set([fld.split('__', 1)[0] for fld in fields_to_populate])
    #         # print "In populate, fields_to_populate before \n%s\nand after\n%s\n" % (
    #         #     fields_to_populate, new_fields_to_populate)
    #         newfields = [(name, fld) for (name, fld) in iteritems(self._fields) if name in new_fields_to_populate]
    #     else:
    #         newfields = iteritems(self._fields)
    #     for name, field in newfields:
    #         if isinstance(field, f.FormField) and getattr(obj, name, None) is None and field._obj is None:
    #             field._obj = field.model_class()  # new instance created
    #         if isinstance(field, f.FileField) and field.data == '':
    #             # Don't try to write empty FileField
    #             continue
    #         field.populate_obj(obj, name)


class ArticleBaseForm(ImprovedBaseForm):
    def process(self, formdata=None, obj=None, **kwargs):
        super(ArticleBaseForm, self).process(formdata, obj, **kwargs)
        # remove all *article fields that don't match new type
        typedata = Article.type_data_name(self.data.get("type", "default"))
        for embedded_type in EMBEDDED_TYPES:
            if embedded_type != typedata:
                del self._fields[embedded_type]

    def populate_obj(self, obj, fields_to_populate=None):
        if not type(obj) is Article:
            raise TypeError("ArticleBaseForm can only handle Article models")
        if "type" in self.data:
            new_type = self.data["type"]
            # Tell the Article we have changed type
            obj.change_type(new_type)
        super(ArticleBaseForm, self).populate_obj(obj, fields_to_populate)


class TagField(SelectMultipleField):
    def __init__(self, model, **kwargs):
        self.model = model
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
        for value in self.model.objects().distinct("tags"):
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
            raise ValueError(self.gettext("Invalid choice(s): one or more data inputs could not be coerced"))


class SelectizeWidget(object):
    def __init__(self, html_tag="ul", prefix_label=True):
        self.html_tag = 'input type="text"'  # ignore
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        kwargs.setdefault("name", field.id)
        html_class = kwargs.get("class", "")
        kwargs["class"] = html_class + " selectize"

        return HTMLString(
            '<%s %s value="%s">'
            % (self.html_tag, html_params(**kwargs), ", ".join([item.slug for item in field.data]))
        )


class ThumbSelectWidget(Select):
    # Modofied __call__ that takes all arguments returned from field.iter_choices,
    # allowing custom data-attributes for example
    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        if self.multiple:
            kwargs["multiple"] = True
        html = ["<select %s>" % html_params(name=field.name, **kwargs)]
        for val, label, selected, option_kwargs in field.iter_choices():
            html.append(self.render_option(val, label, selected, **option_kwargs))
        html.append("</select>")
        return HTMLString("".join(html))


class HiddenModelField(ModelSelectField):
    widget = HiddenInput()

    def _value(self):
        return self.data.id if self.data else None


class OrderedModelSelectMultipleField(ModelSelectMultipleField):

    widget = ThumbSelectWidget(multiple=True)

    # Replaces inherited iter_choices with one that yields selected items first in right order
    def iter_choices(self):
        if self.allow_blank:
            yield ("__None", self.blank_text, self.data is None, {})

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
            kwargs = {}
            if hasattr(obj, "thumb_url"):
                kwargs["data-thumb-url"] = getattr(obj, "thumb_url", "")
            if isinstance(self.widget, ThumbSelectWidget):
                yield (obj.id, label, True, kwargs)
            else:
                yield (obj.id, label, True)
        for obj in self.queryset[
            :100
        ]:  # TODO crazy hack. Some query sets result in too many objects, so we cap it at 100
            label = self.label_attr and getattr(obj, self.label_attr) or obj
            kwargs = {}
            if hasattr(obj, "thumb_url"):
                kwargs["data-thumb-url"] = getattr(obj, "thumb_url", "")
            if obj not in selected:
                if isinstance(self.widget, ThumbSelectWidget):
                    yield (obj.id, label, False, kwargs)
                else:
                    yield (obj.id, label, False)

    def process_formdata(self, valuelist):
        super(OrderedModelSelectMultipleField, self).process_formdata(valuelist)
        if self.data and len(self.data) > 1:
            # Sort based on the order of the valuelist given
            self.data.sort(key=lambda obj: valuelist.index(str(obj.id)))


class CheckboxListWidget(object):
    """
    Renders a list of fields as a `ul` or `ol` list.

    This is used for fields which encapsulate many inner fields as subfields.
    The widget will try to iterate the field to get access to the subfields and
    call them to render them.

    If `prefix_label` is set, the subfield's label is printed before the field,
    otherwise afterwards. The latter is useful for iterating radios or
    checkboxes.
    """

    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        kwargs.setdefault("class", "form-group")
        html = ["<%s %s>" % ("div", html_params(**kwargs))]
        for subfield in field:
            html.append('<div class="checkbox-inline">%s %s</div>' % (subfield(), subfield.label))
        html.append("</div>")
        return HTMLString("".join(html))


class DisabledField(StringField):
    """A disabled field assumes it has default data that should be displayed when rendered but will ignore
    input from forms"""

    def process(self, formdata, data=unset_value):
        # Ignore formdata input, otherwise proceed as normal
        if data == unset_value:
            raise ValueError("DisabledField needs to be explicitly set to a default value")
        self.flags.disabled = True
        super(StringField, self).process(None, data)


class ImprovedModelConverter(ModelConverter):
    @converts("EmbeddedDocumentField")
    def conv_EmbeddedDocument(self, model, field, kwargs):
        """An improved converter for the EmbeddedDocumentField. It uses the CSRF-less form class
        to not get repeated CSRF in the same parent form (automatically added by flask-wtf).
        It uses the ImprovedModelConverter also to fields within the EmbeddedDocument.
        Finally, it will pick up `only` and `exclude` lists from Mongoengine field)."""

        only = getattr(field, "only", []) + kwargs.pop("only", [])
        exclude = getattr(field, "exclude", []) + kwargs.pop("exclude", [])
        field_args = kwargs.pop("field_args", None)
        form_class = kwargs.pop("form_class", None)
        kwargs = {
            "validators": [],
            "filters": [],
            "default": field.default or field.document_type_obj,
            # This separator is added between parent and child field names to see the hierarchy.
            # Using __ means we use the same naming scheme as mongoengine, e.g 'author__name'.
            # This means we can use the embedded document field names as is for querying Mongoengine.
            # Breaks FieldList if used
            # "separator": "__",
        }

        if not form_class:
            form_class = model_form(
                field.document_type_obj,
                only=only,
                exclude=exclude,
                converter=ImprovedModelConverter(),
                base_class=OrigForm,
                field_args=field_args,
            )
        return f.FormField(form_class, **kwargs)

    @converts("ListField")
    def conv_List(self, model, field, kwargs):
        list_type = kwargs.pop("list_type", "")
        if field.name == "tags" or list_type == "tags":
            return TagField(model=model, **kwargs)
        # elif kwargs.get('list_type', "") == "multicheck":
        #     return MultiCheckboxField(model=model, **kwargs)
        elif isinstance(field.field, ReferenceField):
            kwargs["allow_blank"] = not field.required  # Make reference fields inside listfields to allow blanks
            return OrderedModelSelectMultipleField(model=field.field.document_type, **kwargs)
        if field.field.choices:
            kwargs["multiple"] = True
            return self.convert(model, field.field, kwargs)
        field_args = kwargs.pop("field_args", {})
        unbound_field = self.convert(model, field.field, field_args)
        unacceptable = {"validators": [], "filters": [], "min_entries": kwargs.get("min_entries", 0)}
        kwargs.update(unacceptable)
        return f.FieldList(unbound_field, **kwargs)

    @converts("MapField")
    def conv_MapField(self, model, field, kwargs):
        field_args = kwargs.pop("field_args", {})
        if (
            field.name.endswith("_i18n")
            or field.name.endswith("_translated")
            and "sub_labels" not in kwargs
            and "label" in kwargs
        ):
            kwargs["sub_labels"] = localized_field_labels(kwargs["label"])

        unbound_field = self.convert(model, field.field, field_args)
        unacceptable = {"validators": [], "filters": []}
        kwargs.update(unacceptable)
        return MapFormField(unbound_field, **kwargs)

    @converts("ReferenceField")
    def conv_Reference(self, model, field, kwargs):
        kwargs["allow_blank"] = not field.required
        return ModelSelectField(model=field.document_type, **kwargs)

    @converts("URLField")
    def conv_URL(self, model, field, kwargs):
        kwargs["validators"].append(validators.URL())
        self._string_common(model, field, kwargs)
        kwargs.setdefault("widget", html5.URLInput())  # Set if not set from before
        return NoneStringField(**kwargs)

    @converts("EmailField")
    def conv_Email(self, model, field, kwargs):
        kwargs["validators"].append(validators.Email())
        self._string_common(model, field, kwargs)
        kwargs.setdefault("widget", html5.EmailInput())  # Set if not set from before
        return NoneStringField(**kwargs)

    @converts("IntField")
    def conv_Int(self, model, field, kwargs):
        self._number_common(model, field, kwargs)
        kwargs.setdefault("widget", html5.NumberInput(step="1"))  # Set if not set from before
        return f.IntegerField(**kwargs)

    # Temporarily not used. datetime HTML5 inputs are in unclear support and cant handle seconds
    # @converts('DateTimeField')
    # def conv_DateTime(self, model, field, kwargs):
    #   kwargs.setdefault('widget', html5.DateTimeInput()) # Set if not set from before
    #   return f.DateTimeField(**kwargs)

    @converts("FileField")
    def conv_File(self, model, field, kwargs):
        # TODO add validators
        #     FileRequired(),
        #       FileAllowed(['jpg', 'png'], 'Images only!')
        return f.FileField(**kwargs)

    @converts("StringField")
    def conv_String(self, model, field, kwargs):
        if field.regex:
            kwargs["validators"].append(validators.Regexp(regex=field.regex))
        self._string_common(model, field, kwargs)
        if "password" in kwargs:
            if kwargs.pop("password"):
                return f.PasswordField(**kwargs)
        if (
            field.max_length and field.max_length < 100 or getattr(field, "form", None) == "StringField"
        ):  # changed from original code
            return f.StringField(**kwargs)
        return f.TextAreaField(**kwargs)

    @converts("DynamicField")
    def conv_DynamicField(self, model, field, kwargs):
        return JSONField(**kwargs)


class MapFormField(f.Field):
    """A field that holds a dict of fields within it.

     Arguments:
         f {[type]} -- [description]
    """

    def __init__(self, unbound_field, label=None, validators=None, default=None, sub_labels=None, **kwargs):
        super(MapFormField, self).__init__(label, validators, default=default, **kwargs)
        if self.filters:
            raise TypeError("MapFormField does not accept any filters. Instead, define them on the enclosed field.")
        assert isinstance(unbound_field, UnboundField), "Field must be unbound, not a field class"
        self.unbound_field = unbound_field
        self.sub_labels = sub_labels
        self._prefix = kwargs.get("_prefix", "")
        self._errors = None
        if validators:
            raise TypeError("FormField does not accept any validators. Instead, define them on the enclosed form.")

    def process(self, formdata, dict_data=unset_value):
        """Takes incoming formdata and optional start data to populate the inner fields with.
        Formdata overrides start data.
        Start data is built by provided dict_data (usually from a database object) but it will
        be updated if there is additional data in default data for this field.

        Arguments:
            formdata {[type]} -- [description]

        Keyword Arguments:
            data {[type]} -- [description] (default: {unset_value})
        """
        # TODO how to handle empty strings and None, any special?

        self.entries = {}
        default_data = {}
        try:
            default_data = self.default()
        except TypeError:
            default_data = self.default or {}

        if dict_data is unset_value or not dict_data or not isinstance(dict_data, dict):
            dict_data = default_data
        else:
            # Merge default and provided data, but dict_data overrides default_data
            dict_data = dict(default_data, **dict_data)

        # Subfields, e.g. entries, are defined by formdata, or by pre-configured labels (see MapField converter)
        if formdata:
            keys = set(self._extract_keys(self.name, formdata))
        elif self.sub_labels:
            keys = self.sub_labels.keys()
        else:
            keys = dict_data.keys()

        for key in keys:
            self._add_entry(key, formdata, dict_data.get(key, unset_value))

    def _add_entry(self, key, formdata=None, data=unset_value):
        name = f"{self.short_name}-{key}"
        id = f"{self.id}-{key}"
        bind_kwargs = {
            "form": None,
            "name": name,
            "prefix": self._prefix,
            "id": id,
            "_meta": self.meta,
            "translations": self._translations,
        }
        if self.sub_labels and isinstance(self.sub_labels, dict) and key in self.sub_labels:
            bind_kwargs["label"] = self.sub_labels[key]
        field = self.unbound_field.bind(**bind_kwargs)
        field.process(formdata, data)  # Populate the subfield with it's data
        self.entries[key] = field
        return field

    def _extract_keys(self, prefix, formdata):
        """
        Yield indices of any keys with given prefix (name).

        formdata must be an object which will produce keys when iterated.  For
        example, if field 'foo' contains keys 'foo-0-bar', 'foo-1-baz', then
        the numbers 0 and 1 will be yielded, but not neccesarily in order.
        """
        offset = len(prefix) + 1
        for k in formdata:
            if k.startswith(prefix):
                k = k[offset:].split("-", 1)[0]
                if k:
                    yield k

    def populate_obj(self, obj, name):
        _fake = type(str("_fake"), (object,), {})

        output = {}
        for key in self.entries:
            fake_obj = _fake()
            fake_obj.data = None
            self.entries[key].populate_obj(fake_obj, "data")
            if fake_obj.data is not None:  # Skip None values and their keys, will cause Mongoengine problem anyway
                output[key] = fake_obj.data
        setattr(obj, name, output)

    def validate(self, form, extra_validators=tuple()):
        """
        Validate this MapFormField. Cannot have own validators, will just run validators on subfields.
        """
        if extra_validators:
            raise TypeError("FormField does not accept in-line validators, as it gets errors from the enclosed form.")
        # Run validators on all entries within
        error_count = 0
        for subfield in self:
            if not subfield.validate(form):
                error_count += 1

        return error_count == 0

    @property
    def errors(self):
        if self._errors is None:
            self._errors = dict((name, f.errors) for name, f in self.entries.items() if f.errors)
        return self._errors

    def __iter__(self):
        return iter(self.entries.values())

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, key):
        return self.entries[key]

    @property
    def data(self):
        return {k: f.data for k, f in self.entries.items()}

    widget = widgets.TableWidget()


class ResourceError(Exception):
    default_messages = {
        400: _("Bad request or invalid input"),
        401: _("Unauthorized access, please login"),
        403: _("Forbidden, this is not an allowed operation"),
        404: _("Resource not found"),
        500: _("Internal server error"),
    }

    def __init__(self, status_code, message=None, r=None, field_errors=None, template=None, template_vars=None):
        message = message if message else self.default_messages.get(status_code, "%s" % _("Unknown error"))
        self.r = r
        if r:
            form = getattr(r, "form", None)
            self.field_errors = form.errors if form else None
            self.template = getattr(r, "template", None)
            self.template_vars = r
        if status_code == 400 and field_errors:
            message += ", invalid fields: \n%s" % pprint.pformat(field_errors)
        self.message = message
        self.status_code = status_code

        if field_errors:
            self.field_errors = field_errors
        if template:
            self.template = template
        if template_vars:
            self.template_vars = template_vars

        logger.warning(
            "%d: %s%s",
            self.status_code,
            self.message,
            "\n%s\nin resource: \n%s\nwith formdata:\n%s"
            % (request.url, pprint.pformat(self.r), pprint.pformat(dict(request.form))),
        )
        Exception.__init__(self, "%i: %s" % (status_code, message))


class Authorization(object):
    def __init__(self, is_authorized, message="", privileged=False, only_fields=None, error_code=403):
        self.is_authorized = is_authorized
        self.message = message
        self.error_code = error_code
        self.privileged = privileged
        # Privileged means that this authorization would not apply to the public
        # or a normal user. E.g. a user can only edit their own profile (privilege),
        # or an admin can see other people's orders
        self.only_fields = only_fields

    def __repr__(self):
        return "%s%s" % (
            "Authorized" if self.is_authorized else "UNAUTHORIZED",
            ": %s" % self.message if self.message else "",
        )

    def is_privileged(self):
        return self.privileged

    def __bool__(self):
        return self.is_authorized


# Checks if user is authorized to access this resource
class ResourceAccessPolicy(object):
    translate = {"post": "new", "patch": "edit", "put": "edit", "index": "list", "delete": "edit", "get": "view"}
    new_allowed = Authorization(False, _("Creating new resource is not allowed"), error_code=403)

    def authorize(self, op, user=None, res=None):
        op = self.translate.get(op, op)  # TODO temporary translation between old and new op words, e.g. patch vs edit
        if not user:
            user = g.user

        if op == "list":
            return Authorization(True, _("List is allowed"))

        if op == "new":
            return self.is_user(op, user, res) and (self.is_admin(op, user, res) or self.new_allowed)

        if op == "view":  # If list, resource refers to a parent resource
            if not res:
                return Authorization(True, _("Viewing an empty form is allowed"))
            return (
                self.is_resource_public(op, res)
                or self.is_user(op, user, res)
                and (self.is_admin(op, user, res) or self.is_editor(op, user, res) or self.is_reader(op, user, res))
            )

        if op == "edit" or op == "delete":
            if not res:
                return Authorization(False, _("Can't edit/delete a None resource"), error_code=403)
            return self.is_user(op, user, res) and (self.is_admin(op, user, res) or self.is_editor(op, user, res))

        return self.custom_auth(op, user, res)

    def is_user(self, op, user, res):
        msg = _("%(op)s requires a logged in user", op=op)
        if user:
            return Authorization(True, msg)
        else:
            return Authorization(False, msg, error_code=401)  # 401 means unauthenticated, should log in first

    def is_admin(self, op, user, res):
        if user and user.admin:
            return Authorization(True, _("%(user)s is an admin", user=user), privileged=True)
        else:
            return Authorization(False, _("Need to be logged in with admin access"), error_code=403)

    def is_resource_public(self, op, res):
        return Authorization(False, _("This resource does not support to be public"), error_code=403)

    def is_contribution_allowed(self, op, res):
        return Authorization(False, _("This resource does not support contributions"), error_code=403)

    def is_reader(self, op, user, res):
        return Authorization(False, _("Access rules for readers are undefined and therefore denied"), error_code=403)

    def is_editor(self, op, user, res):
        return Authorization(False, _("Access rules for editors are undefined and therefore denied"), error_code=403)

    def custom_auth(self, op, user, res):
        return Authorization(False, _("No authorization implemented for %(op)s", op=op), error_code=403)
