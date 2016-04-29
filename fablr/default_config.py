# CANNOT CONTAIN ACTUAL SECRETS
# Automatically imported, do not edit for local configuration!
# For local configuration, create a config.py that overrides only the values
# needed. The config.py should not use classes, just global variables.
# All configs that should work need to have a default below, or they will be ignored by the ENV parser.


class Config(object):
    DEBUG = True
    DEBUG_TB_PROFILER_ENABLED = True  # profile time to run, will slow down things
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    # DEBUG_TB_HOSTS = ['127.0.0.1']  # Only allow localhost to access debug toolbar
    # Only set new cookie when old expire. This reduce data sent and simplifies caching.
    SESSION_REFRESH_EACH_REQUEST = False
    # Used by i18n translation using Babel
    BABEL_DEFAULT_LOCALE = 'sv'
    BABEL_AVAILABLE_LOCALES = ['sv', 'en']
    MAIL_DEFAULT_SENDER = 'info@helmgast.se'
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64 MB
    ALLOW_SUBDOMAINS = False


class SecretConfig(object):
    # Replace with mongodb://user:pass@host/dbname in config.py file
    MONGODB_HOST = 'mongodb://localhost@defaultdb'

    SECRET_KEY = 'SECRET'
    # Used by Sparkpost email sending API
    SPARKPOST_API_KEY = 'SECRET'

    # Used by social login with Google
    GOOGLE_CLIENT_ID = 'SECRET'
    GOOGLE_CLIENT_SECRET = 'SECRET'

    # Used by social login with Facebook
    FACEBOOK_APP_ID = 'SECRET'
    FACEBOOK_APP_SECRET = 'SECRET'

    # Used for payments
    STRIPE_SECRET_KEY = 'SECRET'
    STRIPE_PUBLIC_KEY = 'SECRET'
