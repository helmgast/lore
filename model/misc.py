"""
    model.misc
    ~~~~~~~~~~~~~~~~

    Includes helper functions for model classes and other lesser used
    model classes.

    :copyright: (c) 2014 by Raconteur
"""

from raconteur import db
import re
import datetime
from flask.ext.babel import lazy_gettext as _
from slugify import slugify

import logging
from flask import current_app
logger = current_app.logger if current_app else logging.getLogger(__name__)

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

    def to_tuples(self):
        return [(s, self[s]) for s in self.keys()]

def list_to_choices(list):
  return [(s.lower(), _(s)) for s in list]

def now():
    return datetime.datetime.now;

class GeneratorInputList(db.Document):
    name = db.StringField()

    def items(self):
        return GeneratorInputItem.select().where(GeneratorInputItem.input_list == self)

class GeneratorInputItem(db.Document):
    input_list = db.ReferenceField(GeneratorInputList)
    content = db.StringField()

class StringGenerator(db.Document):
    name = db.StringField()
    description = db.StringField()
    generator = None

    def __unicode__(self):
        return self.name

