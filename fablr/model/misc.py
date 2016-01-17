"""
    model.misc
    ~~~~~~~~~~~~~~~~

    Includes helper functions for model classes and other lesser used
    model classes.

    :copyright: (c) 2014 by Helmgast AB
"""

import re
import datetime
from flask.ext.babel import lazy_gettext as _
from slugify import slugify as ext_slugify
from flask.ext.wtf import Form # secure form
import wtforms as wtf
#import RadioField, BooleanField, SelectMultipleField, StringField, wtf.validators, widgets
from wtforms.compat import iteritems
from wtforms.widgets import TextArea
from flask.ext.babel import lazy_gettext as _
from fablr.app import STATE_TYPES, FEATURE_TYPES
import logging
from flask import current_app
from flask.ext.mongoengine import Document # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, DateTimeField, FloatField, URLField, ImageField,
    ReferenceField, BooleanField, ListField, IntField, EmailField, EmbeddedDocumentField)

logger = current_app.logger if current_app else logging.getLogger(__name__)

METHODS = frozenset(['POST', 'PUT', 'PATCH', 'DELETE'])

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
            tuples.append(('',''))
        return tuples

def list_to_choices(list):
  return [(s.lower(), _(s)) for s in list]

def now():
    return datetime.datetime.now;

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

class ApplicationConfigForm(Form):
  backup = wtf.BooleanField(_('Do backup'))
  backup_name = wtf.StringField(_('Backup name'), [ wtf.validators.Length(min=6) ])
  state = wtf.RadioField(_('Application state'), choices=STATE_TYPES)
  features = wtf.SelectMultipleField(_('Application features'), choices=FEATURE_TYPES, option_widget=wtf.widgets.CheckboxInput(),
                                 widget=wtf.widgets.ListWidget(prefix_label=False))

class MailForm(Form):
  to_field = wtf.StringField(_('To'), [wtf.validators.Email(), wtf.validators.Required() ])
  from_field = wtf.StringField(_('From'), [wtf.validators.Email(), wtf.validators.Required() ])
  subject = wtf.StringField(_('Subject'), [wtf.validators.Length(min=1, max=200), wtf.validators.Required()])
  message = wtf.StringField(_('Message'), widget=TextArea())

  def process(self, formdata=None, obj=None, allowed_fields=None, **kwargs):
    # Formdata overrides obj, which overrides kwargs.
    # We need to filter formdata to only touch allowed fields.
    # Finally, we need to only use formdata for the fields it is defined for, rather
    # than default behaviour to reset all fields with formdata, regardless if empty
    for name, field, in iteritems(self._fields):
        # Use formdata either if no allowed_fields provided (all allowed) or
        # if field exist in allowed_fields
        if allowed_fields==None or name in allowed_fields:
          field_formdata = formdata
          print "Field %s will get formdata" % name
        else:
          field_formdata = None
          field.flags.disabled = True
          print "Field %s is disabled from getting formdata" % name

        if obj is not None and hasattr(obj, name):
            field.process(field_formdata, getattr(obj, name))
        elif name in kwargs:
            field.process(field_formdata, kwargs[name])
        else:
            field.process(field_formdata)
