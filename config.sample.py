# Default config file, cannot contain secrets, but use as basis for own config
MONGODB_SETTINGS = {'DB':'raconteurdb'}
SECRET_KEY = 'SECRET'
DEBUG = True
#LOG_FOLDER = '.'
BABEL_DEFAULT_LOCALE = 'sv'
LANGUAGES = {
    'en': 'English',
    'sv': 'Swedish'
}
# If using own gmail for outgoing mail
# MAIL_SERVER='smtp.gmail.com'
# MAIL_PORT=465
# MAIL_USE_SSL=True
# MAIL_USERNAME = 'you@gmail.com'
# MAIL_PASSWORD = 'secret'
# MAIL_DEFAULT_SENDER = 'info@helmgast.se'

CELERY_BROKER_URL = 'amqp://'
CELERY_RESULT_BACKEND = 'amqp'
CELERY_TIMEZONE = 'Europe/Stockholm'
CELERY_ENABLE_UTC = True
CELERY_TASK_SERIALIZER='json'
CELERY_ACCEPT_CONTENT=['json']
CELERY_RESULT_SERIALIZER='json'

GOOGLE_CLIENT_ID = 'yada-yada'
GOOGLE_CLIENT_SECRET = 'yada-yada'
FACEBOOK_APP_ID = 'yada'
FACEBOOK_APP_SECRET = 'yada'
