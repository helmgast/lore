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

CELERY_BROKER_URL = 'mongodb://localhost'
CELERY_RESULT_BACKEND = 'mongodb://localhost'
CELERY_TIMEZONE = 'Europe/Stockholm'
CELERY_ENABLE_UTC = True
