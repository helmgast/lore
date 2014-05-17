from wtforms.validators import Email
import re

mail_regex = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$')

def render_mail(recipients, subject, body=None, template=None, **kwargs):
	# recipients should be list of emails (extract from user before sending)
	# subject is a fixed string
	# body can be a formatting string or HTML template
	# kwargs represents context
	if not template and not body:
		raise TypeError("We need either a body string or a template to render mail!")
	for r in recipients:
		if not mail_regex.match(r):
			raise TypeError("Email %s is not correctly formed" % r)
    if template:
    	body = render_template(template, **kwargs)
    mail = Message(subject,
    	sender="info@helmgast.se",
    	recipients=recipients,
    	body=body)
    return mail