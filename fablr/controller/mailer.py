import logging
import re

from flask import Blueprint, current_app, render_template, request, flash
from flask.ext.babel import lazy_gettext as _
from mongoengine.errors import NotUniqueError
from werkzeug.utils import secure_filename
import wtforms as wtf
from flask.ext.wtf import Form  # secure form
from wtforms.widgets import TextArea

from fablr.controller.resource import parse_out_arg, ResourceError, error_response
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
    for r in recipients+cc:
        if not mail_regex.match(r):
            raise TypeError("Email %s is not correctly formed" % r)
    if current_app.debug:
        recipients = [current_app.config['MAIL_DEFAULT_SENDER']]
        message_subject = u'DEBUG: %s' % message_subject

    sender = {
        # Always need to send from default sender, e.g. our verified domain
        'email': current_app.config['MAIL_DEFAULT_SENDER'],
        'name': sender_name
    }

    template = ('mail/%s.html' % mail_type) if not custom_template else custom_template

    rv = mail_app.sparkpost_client.transmission.send(
        recipients=recipients,
        subject=message_subject,
        from_email=sender,
        reply_to=reply_to,
        cc=cc,
        inline_css=True,
        html=render_template(template, **kwargs))
    logger.info("Sent email %s to %s" % (message_subject, recipients))


class MailForm(Form):
    to_field = wtf.StringField(_('To'), [wtf.validators.Email(), wtf.validators.Required()])
    from_field = wtf.StringField(_('From'), [wtf.validators.Email(), wtf.validators.Required()])
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


def disable_fields(form, *fields):
    for f in fields:
        if request.method == 'GET':
            form[f].flags.disabled = True
        else:
            form.__delitem__(f)

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
            user = User.objects(id=user).get()
        order = request.args.get('order', None)
        if order:
            order = Order.objects(id=order).get()
        publisher = request.args.get('publisher', None)
        if publisher:
            publisher = Publisher.objects(slug=publisher).get()
    except Exception as e:
        raise ResourceError(404, message=e.message)

    # parent_template = parse_out_arg(request.args.get('out', None))
    mail = {'to_field':'', 'from_field': server_mail, 'subject': '', 'message': ''}

    mailform = MailForm()
    if mail_type == 'compose':
        disable_fields(mailform, 'to_field')
        mail['to_field'] = server_mail
        mail['from_field'] = user.email if user else ''
    elif mail_type == 'invite':
        mail['subject'] = _('Invitation to join Helmgast.se')
        disable_fields(mailform, 'from_field', 'subject')
        del mailform.message
    elif mail_type == 'verify':
        mail['subject'] =_('%(user)s, welcome to Helmgast!', user=user.display_name())
        mail['to_field'] = user.email
        disable_fields(mailform, 'from_field', 'subject')
        del mailform.message
    elif mail_type == 'order':
        mail['subject'] = _('Order confirmation on helmgast.se')
        mail['to_field'] = user.email
        disable_fields(mailform, 'from_field', 'subject')
        del mailform.message
    elif mail_type == 'remind':
        mail['subject'] = _('Reminder on how to login to Helmgast.se')
        mail['to_field'] = user.email
        disable_fields(mailform, 'from_field', 'subject')
        del mailform.message

    mailform.process(request.form, **mail)  # Enter form input if post, and set defaults from mail-dict made above

    template_vars = {'mail_type': mail_type, 'user': user, 'order': order,
                     'publisher': publisher, 'mailform': mailform}
    if mail_type == 'invite':
        template_vars['token'] = create_token(mailform.to_field.data)

    if request.method == 'POST':
        # Remove all disabled fields from above
        if mailform.validate():
            # Overwrite mail only from fields not disabled, even if those shouldn't have posted data
            mail.update(mailform.data)
            template_vars.update(mail)
            if mail_type == 'invite':
                if not template_vars.get('token', None):
                    return error_response(render_template('mail/mail_post.html', **template_vars), 400,
                                          _("No token could be generated from email"))
                # We should create an invited user to match when link is clicked
                user = User(email=mail['to_field'])
                try:
                    user.save()
                except NotUniqueError as e:
                    return error_response(render_template('mail/mail_post.html', **template_vars), 400,
                                          _("User already exists"))
            cc = [mail['from_field']] if mail_type == 'compose' else None  # Cc mail to the sender for reference
            send_mail([mail['to_field']], mail['subject'], reply_to=mail['from_field'], cc=cc, **template_vars)
            flash(_('Sent email "%(subject)s" to %(recipients)s', subject=mail['subject'],
                    recipients=mail['to_field']), 'success')
            return "Mail sent!"
        else:
            return error_response(render_template('mail/mail_post.html', **template_vars), 400, _("Errors in form"))

    template_vars.update(mail)
    # No need to do anything special for GET
    return render_template(mail_template, **template_vars)
