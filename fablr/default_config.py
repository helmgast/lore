# CANNOT CONTAIN SECRETS
# Automatically imported, do not edit for local configuration
# For local configuration, edit local_config.py
# Local config needs to be pointed to by environment variable RACONTEUR_CONFIG_FILE

# format mongodb://user:pass@localhost/dbname replace in local config
MONGODB_HOST = ''

LOG_FOLDER = ''

SECRET_KEY = 'SECRET'

DEBUG = True
DEBUG_TB_HOSTS = ['127.0.0.1'] # Only allow localhost to access debug toolbar
#LOG_FOLDER = '.'

# Used by i18n translation using Babel
BABEL_DEFAULT_LOCALE = 'sv'

# Used by Mandrill email sending API
MANDRILL_API_KEY = 'SECRET'
MAIL_DEFAULT_SENDER = 'info@helmgast.se'

# Used by social login with Google
GOOGLE_CLIENT_ID = 'SECRET'
GOOGLE_CLIENT_SECRET = 'SECRET'

# Used by social login with Facebook
FACEBOOK_APP_ID = 'SECRET'
FACEBOOK_APP_SECRET = 'SECRET'

# Used for payments
STRIPE_SECRET_KEY = 'SECRET'
STRIPE_PUBLIC_KEY = 'SECRET'

CELERY_BROKER_URL = 'amqp://'
CELERY_RESULT_BACKEND = 'amqp'
CELERY_TIMEZONE = 'Europe/Stockholm'
CELERY_ENABLE_UTC = True
CELERY_TASK_SERIALIZER='json'
CELERY_ACCEPT_CONTENT=['json']
CELERY_RESULT_SERIALIZER='json'