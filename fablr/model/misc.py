"""
    model.misc
    ~~~~~~~~~~~~~~~~

    Includes helper functions for model classes and other lesser used
    model classes.

    :copyright: (c) 2014 by Helmgast AB
"""
from collections import namedtuple, OrderedDict
from datetime import timedelta, date, datetime
from urlparse import urlparse

import unicodedata
from babel import Locale
from babel.dates import get_month_names
from dateutil.relativedelta import *

import flask_mongoengine
import wtforms as wtf
from flask import g, request
from flask_wtf import Form  # secure form
from slugify import slugify as ext_slugify

from wtforms.compat import iteritems
from wtforms.widgets import TextArea
from flask_babel import lazy_gettext as _, get_locale, format_date, format_timedelta
import logging
from flask import current_app
from mongoengine import (EmbeddedDocument, StringField, ReferenceField)

from fablr.extensions import configured_locales

logger = current_app.logger if current_app else logging.getLogger(__name__)

METHODS = frozenset(['POST', 'PUT', 'PATCH', 'DELETE'])

Document = flask_mongoengine.Document
# Turns off automatic index creation because if DB errors out, it would happen at import time
# Document._meta['auto_create_index'] = True

def slugify(title):
    slug = ext_slugify(title)
    if slug.upper() in METHODS:
        return "%s_" % slug
    else:
        return slug


class Choices(dict):
    # def __init__(self, *args, **kwargs):
    #     if args:
    #         return dict.__init__(self, [(slugify(k), _(k)) for k in args])
    #     elif kwargs:
    #         return dict.__init__(self, {k:_(k) for k in kwargs})

    def __getattr__(self, name):
        if name in self.keys():
            return name
        raise AttributeError(name)

    def to_tuples(self, empty_value=False):
        tuples = [(s, self[s]) for s in self.keys()]
        if empty_value:
            tuples.append(('', ''))
        return tuples


def list_to_choices(list):
    return [(s.lower(), _(s)) for s in list]


def translate_action(action, item):
    if action == 'patch':
        return _('"%(item)s" edited', item=item)
    elif action == 'post':
        return _('"%(item)s" created', item=item)
    elif action == 'put':
        return _('"%(item)s" replaced', item=item)
    elif action == 'delete':
        return _('"%(item)s" deleted', item=item)
    elif action == 'completed_profile':
        return _('Completed profile')
    elif action == 'purchase':
        return _('Purchased "%(item)s"', item=item)
    else:
        return action


FilterOption = namedtuple('FilterOption', 'kwargs label')


def numerical_options(field_name, spans=None, labels=None):
    rv = []
    if not spans:
        raise ValueError("Need at least one value to span options for")
    own_labels = isinstance(labels, list)
    if own_labels and len(labels) != len(spans) + 1:
        raise ValueError("Need one label more than items in spans, as the last label 'More than [last value of spans]'")
    for idx, span in enumerate(spans):
        if own_labels:
            rv.append(FilterOption(kwargs={field_name + '__lte': span, field_name + '__gt': None}, label=labels[idx]))
        else:
            rv.append(FilterOption(kwargs={field_name + '__lte': span, field_name + '__gt': None},
                                   label=_('Less than %(val)s', val=span)))
    # Add last filter value, as more than the highest value of span
    if own_labels:
        rv.append(FilterOption(kwargs={field_name + '__gt': spans[-1], field_name + '__lte': None}, label=labels[-1]))
    else:
        rv.append(FilterOption(kwargs={field_name + '__gt': spans[-1], field_name + '__lte': None},
                               label=_('More than %(val)s', val=spans[-1])))

    def return_function(*args):
        return rv

    return return_function


def reference_options(field_name, model):
    def return_function(*args):
        return [FilterOption(kwargs={field_name: o.slug}, label=o.title) for o in model.objects().distinct(field_name)]

    return return_function


def choice_options(field_name, choices):
    rv = [FilterOption(kwargs={field_name: a}, label=b) for a, b in choices]

    def return_function(*args):
        return rv

    return return_function


def datetime_month_options(field_name):
    """
    Creates a range of last 12 months starting with current month, e.g. each month is
    field__gte=year/month/1, field__lt=year/month+1/1
    :param field_name:
    :return:
    """

    def return_function(*args):
        # Rebuild above list of tuples to one with dict, and make time - timedelta
        now = date.today().replace(day=1)  # Reset day to first of month
        # now = datetime(year=now.year, month=now.month, day=1)
        rv = []
        for i in range(0, 11):
            rv.append(FilterOption(kwargs={
                field_name + '__gte': now+relativedelta(months=-i),
                field_name + '__lt': now+relativedelta(months=-i+1)}, label=format_date(now+relativedelta(months=-i), 'MMMM')))
        return rv

    return return_function


def datetime_delta_options(field_name, time_deltas=None, delta_labels=None):
    if not time_deltas:
        raise ValueError("Need at least one value in time_deltas")
    if delta_labels and len(delta_labels) is not len(time_deltas):
        raise ValueError("Length of delta_labels is not matching length of time_deltas")

    def return_function(*args):
        rv = []
        today = date.today()
        for i in range(0, len(time_deltas)):
            delta = time_deltas[i]
            rv.append(FilterOption(kwargs={field_name + '__gte': today-delta, field_name + '__lt': None},
                                   label=_('Last %(delta)s', delta=delta_labels[i] if delta_labels else format_timedelta(delta))))
        # Add a last "older than all above" option
        rv.append(FilterOption(kwargs={field_name + '__lt': today - time_deltas[-1], field_name + '__gte': None},
                               label=_('Older than %(delta)s', delta=format_timedelta(time_deltas[-1]))))
        return rv

    return return_function


from7to365 = [timedelta(days=7), timedelta(days=30), timedelta(days=90), timedelta(days=365)]


def distinct_options(field_name, model):
    def return_function(*args):
        values = model.objects().distinct(field_name)
        rv = [FilterOption(kwargs={field_name: v}, label=v) for v in values]
        return rv

    return return_function

available_locale_tuples = [(code, Locale.parse(code).language_name.capitalize()) for code in configured_locales]

# Enumerates all country codes based on Babel (ISO 3166). Exclude regions (3 letter codes) and special code ZZ
country_codes = [code for code in Locale('en').territories.iterkeys() if len(code) == 2 and not code == 'ZZ']  # Skip non-2-letter codes


class CountryChoices:
    """
    Lazily build lists of country choices with local translation and sorted alphabetically
    """

    def __init__(self):
        # self.i = 0
        self.dicts = {}

    def refresh(self):
        new_loc = get_locale()
        key = str(new_loc)
        if key not in self.dicts:
            countries = [(code, new_loc.territories[code]) for code in country_codes]
            self.dicts[key] = OrderedDict(sorted(countries, key=lambda tup: tup[1]))
        return self.dicts[key]

    def __iter__(self):
        """
        Return an iterator over its tuples of (code, country_name). Called by wtforms.SelectField
        :return:
        """
        d = self.refresh()
        return d.iteritems()

    # def next(self):  # Python 3: def __next__(self)
    #     if self.i >= len(self.tuples)-1:  # len=3, if i is 2 then stop
    #         self.i = 0
    #         raise StopIteration
    #     else:
    #         self.i += 1
    #         return self.tuples[self.i]

    def __getitem__(self, k):
        """
        This is a hack, MongoEngine checks if first object is a list or tuple, this will make it NOT be
        :param k:
        :return:
        """
        return country_codes[0]

    def __contains__(self, item):
        """
        Called by MongoEngine to check if choice exists inside
        :param item:
        :return:
        """
        d = self.refresh()
        return item in d

class Address(EmbeddedDocument):
    name = StringField(max_length=60, required=True, verbose_name=_('Name'))
    street = StringField(max_length=60, required=True, verbose_name=_('Street'))
    zipcode = StringField(max_length=8, required=True, verbose_name=_('ZIP Code'))
    city = StringField(max_length=60, required=True, verbose_name=_('City'))
    # Tuples come unsorted, let's sort first
    country = StringField(choices=CountryChoices(), required=True,
                          default='SE',
                          verbose_name=_('Country'))
    mobile = StringField(max_length=14, verbose_name=_('Cellphone Number'))


class GeneratorInputList(Document):
    name = StringField()

    def items(self):
        return GeneratorInputItem.select().where(GeneratorInputItem.input_list == self)


class GeneratorInputItem(Document):
    input_list = ReferenceField(GeneratorInputList)
    content = StringField()


class StringGenerator(Document):
    name = StringField()
    description = StringField()
    generator = None

    def __unicode__(self):
        return self.name

# From Django https://github.com/django/django/blob/master/django/utils/http.py
# Note, changed url_info = _urlparse(url) to urlparse(url), e.g. use stdlib urlparse instead of django's
def _is_safe_url(url, allowed_hosts, require_https=False):
    # Chrome considers any URL with more than two slashes to be absolute, but
    # urlparse is not so flexible. Treat any url with three slashes as unsafe.
    if url.startswith('///'):
        return False
    url_info = urlparse(url)
    # Forbid URLs like http:///example.com - with a scheme, but without a hostname.
    # In that URL, example.com is not the hostname but, a path component. However,
    # Chrome will still consider example.com to be the hostname, so we must not
    # allow this syntax.
    if not url_info.netloc and url_info.scheme:
        return False
    # Forbid URLs that start with control characters. Some browsers (like
    # Chrome) ignore quite a few control characters at the start of a
    # URL and might consider the URL as scheme relative.
    if unicodedata.category(url[0])[0] == 'C':
        return False
    scheme = url_info.scheme
    # Consider URLs without a scheme (e.g. //example.com/p) to be http.
    if not url_info.scheme and url_info.netloc:
        scheme = 'http'
    valid_schemes = ['https'] if require_https else ['http', 'https']
    return ((not url_info.netloc or url_info.netloc in allowed_hosts) and
            (not scheme or scheme in valid_schemes))


def safe_next_url(default_url=None):
    rv = request.args.get('next', None)
    if rv:
        allowed_hosts = [request.host]
        if 'DEFAULT_URL' in current_app.config:
            allowed_hosts.append(current_app.config['DEFAULT_URL'])
        if _is_safe_url(rv, allowed_hosts):
            return rv
        else:
            # Do this check only if previous failed as we will need to query DB for all hosts
            from fablr.model.world import Publisher
            q = Publisher.objects().only('slug')
            if len(q):
                allowed_hosts.extend(pub.slug for pub in q)
                if _is_safe_url(rv, allowed_hosts):
                    return rv
    return default_url
