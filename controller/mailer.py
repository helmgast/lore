from wtforms.validators import Email
from flask import Blueprint, current_app, render_template, request, redirect, abort
from werkzeug.utils import secure_filename
from werkzeug.datastructures import ImmutableMultiDict
from flask.ext.babel import gettext as _
from model.user import User
from model.shop import Order
from model.web import MailForm
from controller.resource import parse_out_arg, ResourceError
import re

logger = current_app.logger if current_app else logging.getLogger(__name__)

mail_regex = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$')

mail_app = Blueprint('mail', __name__, template_folder='../templates/mail')

def send_mail(recipients, message_subject, mail_type, custom_template=None, 
    sender=None, **kwargs):
  # recipients should be list of emails (extract from user before sending)
  # subject is a fixed string
  # template is the template object or path
  # sender is an email or a tuple (email, name)
  # kwargs represents context for the template to render correctly
  for r in recipients:
    if not mail_regex.match(r):
      raise TypeError("Email %s is not correctly formed" % r)
  if current_app.debug:
    recipients = [current_app.config['MAIL_DEFAULT_SENDER']]
    message_subject = u'DEBUG: %s' % message_subject

  if not sender:
    sender = (current_app.config['MAIL_DEFAULT_SENDER'], 'Helmgast')
  
  template = ('mail/%s.html' % mail_type) if not custom_template else custom_template

  message = {
    'to': [{'email':email} for email in recipients],
    'subject': message_subject,
    'from_email': sender[0] if isinstance(sender, tuple) else sender,
    'from_name': sender[1] if isinstance(sender, tuple) else None,
    'inline_css': True,
    'html': render_template(template, **kwargs)
  }

  mail_app.mandrill_client.messages.send(message=message)
  logger.info("Sent email %s to %s" % (message['subject'], message['to']))

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

@mail_app.route('/<mail_type>', methods=['GET', 'POST'])
@current_app.admin_required
def mail_view(mail_type):
  mail_type = secure_filename(mail_type)
  mail_template = 'mail/%s.html' % mail_type
  server_mail = current_app.config['MAIL_DEFAULT_SENDER']
  if mail_type not in ['compose', 'remind_login', 'order', 'verify', 'invite']:
    raise ResourceError(404)
  user = request.args.get('user', None)
  try:
    if user:
      user = User.objects(id=user).get()
    order = request.args.get('order', None)
    if order:
      order = Order.objects(id=order).get()
  except Exception as e:
    raise ResourceError(404, message=e.message)
  parent_template = parse_out_arg(request.args.get('out', None))
  if mail_type == 'compose':
    writable = {'from_field', 'subject', 'message'}
    overrides = {'to_field': server_mail}
  elif mail_type == 'invite':
    writable = {'to_field'}
    overrides = {'from_field': server_mail, 'subject':_('Invitation to join Helmgast.se')}
  else:
    if mail_type == 'verify':
      subject = _('%(user)s, welcome to Helmgast!', user=user.display_name())
    elif mail_type == 'order':
      subject = _('Thank you for your order!')
    elif mail_type == 'remind_login':
      subject = _('Reminder on how to login to Helmgast.se')
    writable = {}
    overrides = {'from_field': server_mail, 'to_field':user.email, 'subject':subject}
  
  if request.method == 'GET':
    mailform = MailForm(request.args, 
      allowed_fields=writable,
      **overrides)
    return render_template(mail_template,
      mail_type=mail_type, 
      parent_template=parent_template, 
      user=user,
      order=order,
      mailform=mailform, **mailform.data)
  
  elif request.method == 'POST':
    mailform = MailForm(request.form, 
      allowed_fields=writable,
      **overrides)
    if mailform.validate():
      email = send_mail(
        [mailform.to_field.data], 
        mailform.subject.data, 
        mail_type=mail_type,
        sender=mailform.from_field.data,
        user=user,
        order=order, **mailform.data)
      return "Mail sent!"
    else:
      raise ResourceError(400, form=mailform)
  else:
    raise ResourceError(403)
