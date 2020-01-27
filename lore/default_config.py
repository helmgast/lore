# CANNOT CONTAIN ACTUAL SECRETS
# Automatically imported, do not edit for local configuration!
# For local configuration, create a config.py that overrides only the values
# needed. The config.py should not use classes, just global variables.
# All configs that should work need to have a default below, or they will be ignored by the ENV parser.

class Config(object):
    PRODUCTION = False
    DEBUG = True
    DEBUG_TB_PROFILER_ENABLED = True  # profile time to run, will slow down things
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    DEBUG_TB_PANELS = (
                'flask_debugtoolbar.panels.versions.VersionDebugPanel',
                'flask_debugtoolbar.panels.timer.TimerDebugPanel',
                'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
                'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
                'flask_debugtoolbar.panels.config_vars.ConfigVarsDebugPanel',
                'flask_debugtoolbar.panels.template.TemplateDebugPanel',
                'flask_debugtoolbar.panels.sqlalchemy.SQLAlchemyDebugPanel',
                'flask_debugtoolbar.panels.logger.LoggingPanel',
                'lore.extensions.PatchedRouteListDebugPanel',
                'flask_debugtoolbar.panels.profiler.ProfilerDebugPanel',
            )
    # DEBUG_TB_HOSTS = ['127.0.0.1']  # Only allow localhost to access debug toolbar
    # Only set new cookie when old expire. This reduce data sent and simplifies caching.
    SESSION_REFRESH_EACH_REQUEST = False
    # Used by i18n translation using Babel
    BABEL_DEFAULT_LOCALE = 'sv_SE'
    BABEL_DEFAULT_TIMEZONE = 'Europe/Stockholm'
    # Locales that can be selected throughout the system
    BABEL_AVAILABLE_LOCALES = ['sv_SE', 'en_US']  # In order of preference for some cases
    MAIL_DEFAULT_SENDER = 'info@helmgast.se'
    MAX_CONTENT_LENGTH = 256 * 1024 * 1024  # 256 MB
    DEFAULT_HOST = 'localhost:5000'  # Default host when not using flask dev server
    DEBUG_MAIL_OVERRIDE = 'martin@helmgast.se'
    VERSION = "No Version"
    WEBPACK_MANIFEST_PATH = '../static/manifest.json'
    GOOGLE_SERVICE_ACCOUNT_PATH = "google_service_account.json" # Relative to root, as import tools run at CWD root
    PREFERRED_URL_SCHEME = ''  # Protocol relative URLs in case no request context
    PLUGIN_PATH = '/data/www/github/'
    URL_PREFIX = None  # Set to /something to add that as URL prefix globally for the app
    CLOUDINARY_DOMAIN = None
    

class SecretConfig(object):
    # Replace with mongodb://user:pass@host/dbname in config.py file
    MONGODB_HOST = 'mongodb://localhost@defaultdb'

    SECRET_KEY = 'SECRET'
    # Used by Sparkpost email sending API
    SPARKPOST_API_KEY = 'SECRET'

    SENTRY_DSN = 'SECRET'

    # Used to access Auth0 authentication backend
    AUTH0_CLIENT_SECRET = 'SECRET'
    AUTH0_CLIENT_ID = 'SECRET'
    AUTH0_DOMAIN = 'SECRET'

    # Used for payments
    STRIPE_SECRET_KEY = 'SECRET'
    STRIPE_PUBLIC_KEY = 'SECRET'

    GITHUB_WEBHOOK_KEY = 'SECRET'
