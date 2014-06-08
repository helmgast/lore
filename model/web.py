"""
    model.web
    ~~~~~~~~~~~~~~~~

    Classes that aren't meant to be saved to db.

    :copyright: (c) 2014 by Raconteur
"""


from wtforms import Form, RadioField, BooleanField, SelectMultipleField, StringField, validators, widgets
from flask.ext.babel import lazy_gettext as _
from raconteur import STATE_TYPES, FEATURE_TYPES


class ApplicationConfigForm(Form):
  backup = BooleanField(_('Do backup'))
  backup_name = StringField(_('Backup name'), [ validators.Length(min=6) ])
  state = RadioField(_('Application state'), choices=STATE_TYPES)
  features = SelectMultipleField(_('Application features'), choices=FEATURE_TYPES, option_widget=widgets.CheckboxInput(),
                                 widget=widgets.ListWidget(prefix_label=False))

class AdminEmailForm(Form):
	to_field = StringField(_('To'), [validators.Email(), validators.Required() ])
	subject = StringField(_('Subject'), [validators.Length(min=1, max=200), validators.Required()])
	message = StringField(_('Message'), [validators.Length(min=1), validators.Required()])