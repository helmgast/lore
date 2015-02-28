from wtforms.validators import Email
from flask import Blueprint, current_app, render_template, request, redirect, abort
from werkzeug.utils import secure_filename
from extensions import MailMessage
from model.user import User
from model.shop import Order
from model.web import EmailForm
from resource import parse_out_arg
import re

logger = current_app.logger if current_app else logging.getLogger(__name__)

mail_regex = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$')

mail_app = Blueprint('mail', __name__, template_folder='../templates/mail')

def render_mail(recipients, subject, sender=None, body=None, template=None, **kwargs):
  # recipients should be list of emails (extract from user before sending)
  # subject is a fixed string
  # body can be a formatting string or HTML template
  # kwargs represents context
  for r in recipients:
    if not mail_regex.match(r):
      raise TypeError("Email %s is not correctly formed" % r)
  mailargs = {'recipients':recipients, 'subject':subject}
  if sender:
    mailargs['sender']=sender
  if template:
    mailargs['html'] = render_template(template, **kwargs)
  elif body:
    mailargs['body'] = body
  else:
    raise TypeError("We need either a body string or a template to render mail!")
  mailargs['extra_headers'] = {'X-MC-InlineCSS':'true'} # Inline CSS in template
  return MailMessage(**mailargs)


# GET
# 1) Load model to form
# 2) Parse prefills into dict (only matching fields)
# 3) Load additional defaults, overriding prefills
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
  user = request.args.get('user', None)
  if user:
    user = User.objects(id=user).get()
  order = request.args.get('order', None)
  if order:
    order = Order.objects(id=order).get()
  parent_template = parse_out_arg(request.args.get('out', None))
  mailform = EmailForm()
  if request.method == 'GET':
    return render_template('mail/%s.html' % mail_type, 
      mail_type=mail_type, 
      parent_template=parent_template, 
      user=user,
      order=order,
      mailform=mailform)
  elif request.method == 'POST' and user:
    mailform = EmailForm(request.form)
    mailform.to_field.data = user.email
    if mailform.validate():
      email = render_mail(
        ['ripperdoc@gmail.com'], 
        mailform.subject.data , 
        template='mail/%s.html' % mail_type, 
        user=user,
        order=order)
      email.send_out()
      return "Mail sent!"
    else:
      print mailform.errors
      abort(400)  
  else:
    abort(400)