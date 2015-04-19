# Default config file, cannot contain secrets, but use as basis for own config
MONGODB_SETTINGS = {'DB':'raconteurdb'}
SECRET_KEY = 'SECRET'
DEBUG = True
#LOG_FOLDER = '.'

# Used by i18n translation using Babel
BABEL_DEFAULT_LOCALE = 'sv'

# Used by Mandrill email sending API
MANDRILL_API_KEY = 'yada-yada'
MAIL_DEFAULT_SENDER = 'info@helmgast.se'

# Used by social login with Google
GOOGLE_CLIENT_ID = 'yada-yada'
GOOGLE_CLIENT_SECRET = 'yada-yada'

# Used by social login with Facebook
FACEBOOK_APP_ID = 'yada-yada'
FACEBOOK_APP_SECRET = 'yada-yada'

# Used for payments
STRIPE_SECRET_KEY = 'yada-yada'
STRIPE_PUBLIC_KEY = 'yada-yada'

CELERY_BROKER_URL = 'amqp://'
CELERY_RESULT_BACKEND = 'amqp'