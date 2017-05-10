import logging
import re
import urllib

from flask import Blueprint, current_app, render_template, request, flash
from flask_babel import lazy_gettext as _
from mongoengine.errors import NotUniqueError
from werkzeug.utils import secure_filename
import wtforms as wtf
from flask_wtf import Form  # secure form
from wtforms.widgets import TextArea

from fablr.controller.resource import parse_out_arg, ResourceError, DisabledField
from fablr.model.baseuser import create_token
from fablr.model.shop import Order
from fablr.model.user import User
from fablr.model.world import Publisher

logger = current_app.logger if current_app else logging.getLogger(__name__)

mail_regex = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$')

mail_app = Blueprint('mail', __name__, template_folder='../templates/mail')


def send_mail(recipients, message_subject, mail_type, custom_template=None,
              reply_to=None, cc=[], sender_name='Helmgast', **kwargs):
    # recipients should be list of emails (extract from user before sending)
    # subject is a fixed string
    # template is the template object or path
    # sender is an email or a tuple (email, name)
    # kwargs represents context for the template to render correctly
    for r in recipients + cc:
        if not mail_regex.match(r):
            raise TypeError("Email %s is not correctly formed" % r)
    if current_app.debug and current_app.config['DEBUG_MAIL_OVERRIDE']:
        recipients = [current_app.config['DEBUG_MAIL_OVERRIDE']]
        message_subject = u'DEBUG: %s' % message_subject

    sender = {
        # Always need to send from default sender, e.g. our verified domain
        'email': current_app.config['MAIL_DEFAULT_SENDER'],
        'name': sender_name
    }

    template = ('mail/%s.html' % mail_type) if not custom_template else custom_template

    rv = mail_app.sparkpost_client.transmission.send(
        recipients=recipients,
        subject=unicode(message_subject),
        from_email=sender,
        reply_to=reply_to,
        cc=cc,
        inline_css=True,
        html=render_template(template, **kwargs))
    logger.info(u"Sent email %s to %s" % (message_subject, recipients))


class SystemMailForm(Form):
    """No field in this form can actually be set, as we know who to send to already"""
    to_field = DisabledField(_('To'))
    from_field = DisabledField(_('From'))
    subject = DisabledField(_('Subject'))


class AnyUserSystemMailForm(Form):
    """Here we only ask for the to_field, others are preset"""
    to_field = wtf.StringField(_('To'), [wtf.validators.Email(), wtf.validators.Required()])
    from_field = DisabledField(_('From'))
    subject = DisabledField(_('Subject'))


class UserMailForm(Form):
    """To field is preset as it goes to the publisher, others are open for formdata"""
    from_field = wtf.StringField(_('From'), [wtf.validators.Email(), wtf.validators.Required()])
    to_field = DisabledField(_('To'))
    subject = wtf.StringField(_('Subject'), [wtf.validators.Length(min=1, max=200), wtf.validators.Required()])
    message = wtf.StringField(_('Message'), widget=TextArea())

    # def process(self, formdata=None, obj=None, allowed_fields=None, **kwargs):
    #     # Formdata overrides obj, which overrides kwargs.
    #     # We need to filter formdata to only touch allowed fields.
    #     # Finally, we need to only use formdata for the fields it is defined for, rather
    #     # than default behaviour to reset all fields with formdata, regardless if empty
    #     for name, field, in iteritems(self._fields):
    #         # Use formdata either if no allowed_fields provided (all allowed) or
    #         # if field exist in allowed_fields
    #         if allowed_fields == None or name in allowed_fields:
    #             field_formdata = formdata
    #             print "Field %s will get formdata" % name
    #         else:
    #             field_formdata = None
    #             field.flags.disabled = True
    #             print "Field %s is disabled from getting formdata" % name
    #
    #         if obj is not None and hasattr(obj, name):
    #             field.process(field_formdata, getattr(obj, name))
    #         elif name in kwargs:
    #             field.process(field_formdata, kwargs[name])
    #         else:
    #             field.process(field_formdata)


# GET
# 1) Load model to form
# 2) Parse prefills into dict (only matching fields)
# 3) Load additional defaults, overriding prefills TODO has to be manual
# 4) Overwrite form data with prefills
# 5) Delete form fields not readable
# 6) Render, but disable fields not writable

# POST
# 1) Load formdata to form
# 2) Validate form based on fields not readable or writable
# 3) If valid, validate on other constraints
# 4) Populate object

@mail_app.route('/<any(compose, remind, order, verify, invite):mail_type>', methods=['GET', 'POST'])
@current_app.admin_required
def mail_view(mail_type):
    intent = request.args.get('intent', None)
    if intent == 'post':
        mail_template = 'mail/mail_post.html'
    else:
        mail_template = 'mail/%s.html' % mail_type
    server_mail = current_app.config['MAIL_DEFAULT_SENDER']
    try:
        user = request.args.get('user', None)
        if user:
            user = User.objects(id=user).get()  # May throw DoesNotExist
        order = request.args.get('order', None)
        if order:
            order = Order.objects(id=order).get()  # May throw DoesNotExist
        publisher = request.args.get('pub_host', None)
        if publisher:
            publisher = Publisher.objects(slug=publisher).get()  # May throw DoesNotExist
    except Exception as e:
        # Catch and re-raise as a 404 because incorrect parameter to mail_view
        raise ResourceError(404, message=e.message)

    # parent_template = parse_out_arg(request.args.get('out', None))
    mail = {'to_field': '', 'from_field': server_mail, 'subject': '', 'message': ''}

    if mail_type == 'compose':
        mailform = UserMailForm(request.form, to_field=server_mail, from_field=user.email if user else '',
                                subject=request.args.get('subject', None))
    elif mail_type == 'invite':
        mailform = AnyUserSystemMailForm(request.form, subject=_('Invitation to join Helmgast.se'),
                                         from_field=server_mail)
    elif mail_type == 'verify':
        mailform = SystemMailForm(request.form, subject=_('%(user)s, welcome to Helmgast!', user=user.display_name()),
                                  to_field=user.email, from_field=server_mail)
    elif mail_type == 'order':
        mailform = SystemMailForm(request.form, subject=_('Order confirmation on helmgast.se'),
                                  to_field=user.email, from_field=server_mail)
    elif mail_type == 'remind':
        mailform = SystemMailForm(request.form, subject=_('Reminder on how to login to Helmgast.se'),
                                  to_field=user.email, from_field=server_mail)

    template_vars = {'mail_type': mail_type, 'user': user, 'order': order,
                     'publisher': publisher, 'mailform': mailform}
    if mail_type == 'invite':
        template_vars['token'] = create_token(mailform.to_field.data)

    if request.method == 'POST':
        if mailform.validate():
            mail.update(mailform.data)
            template_vars.update(mail)
            if mail_type == 'invite':
                if not template_vars.get('token', None):
                    return render_template('mail/mail_post.html',
                                           errors=[('danger', _("No token could be generated from email"))],
                                           **template_vars), 400
                # We should create an invited user to match when link is clicked
                user = User(email=mail['to_field'])
                try:
                    user.save()
                except NotUniqueError as e:
                    return render_template('mail/mail_post.html',
                                           errors=[('danger', _("User already exists"))],
                                           **template_vars), 400
            cc = [mail['from_field']] if mail_type == 'compose' else []  # Cc mail to the sender for reference
            send_mail([mail['to_field']], mail['subject'], reply_to=mail['from_field'], cc=cc, **template_vars)
            flash(_('Sent email "%(subject)s" to %(recipients)s', subject=mail['subject'],
                    recipients=mail['to_field']), 'success')
            return "Mail sent!"
        else:
            return render_template('mail/mail_post.html',
                                   errors=[('danger', _("Errors in form"))],
                                   **template_vars), 400

    template_vars.update(mail)
    # No need to do anything special for GET
    return render_template(mail_template, **template_vars)
