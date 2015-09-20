"""
    model.web
    ~~~~~~~~~~~~~~~~

    Classes that aren't meant to be saved to db.

    :copyright: (c) 2014 by Helmgast AB
"""

from flask.ext.wtf import Form # secure form
from wtforms import RadioField, BooleanField, SelectMultipleField, StringField, validators, widgets
from wtforms.compat import iteritems
from wtforms.widgets import TextArea
from flask.ext.babel import lazy_gettext as _
from fablr.app import STATE_TYPES, FEATURE_TYPES

class ApplicationConfigForm(Form):
  backup = BooleanField(_('Do backup'))
  backup_name = StringField(_('Backup name'), [ validators.Length(min=6) ])
  state = RadioField(_('Application state'), choices=STATE_TYPES)
  features = SelectMultipleField(_('Application features'), choices=FEATURE_TYPES, option_widget=widgets.CheckboxInput(),
                                 widget=widgets.ListWidget(prefix_label=False))

class MailForm(Form):
  to_field = StringField(_('To'), [validators.Email(), validators.Required() ])
  from_field = StringField(_('From'), [validators.Email(), validators.Required() ])  
  subject = StringField(_('Subject'), [validators.Length(min=1, max=200), validators.Required()])
  message = StringField(_('Message'), widget=TextArea())

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