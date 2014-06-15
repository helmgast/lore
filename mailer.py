from wtforms.validators import Email
from flask import render_template
from extensions import MailMessage
import re

mail_regex = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$')

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
  return MailMessage(**mailargs)