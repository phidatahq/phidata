import os
import logging
from typing import Optional

from cachelib.redis import RedisCache
from celery.schedules import crontab
from flask_appbuilder.security.manager import AUTH_DB, AUTH_OAUTH
from custom_sso_security_manager import CustomSsoSecurityManager

logger = logging.getLogger()


def get_env_variable(var_name: str, default: Optional[str] = None) -> str:
    """Get the environment variable or raise exception."""
    try:
        return os.environ[var_name]
    except KeyError:
        if default is not None:
            return default
        else:
            error_msg = "The environment variable {} was missing, abort...".format(
                var_name
            )
            raise EnvironmentError(error_msg)


# ----------------------------------------------------
# DATABASE CONFIG
# ----------------------------------------------------
DATABASE_DIALECT = get_env_variable("DATABASE_DIALECT")
DATABASE_USER = get_env_variable("DATABASE_USER")
DATABASE_PASSWORD = get_env_variable("DATABASE_PASSWORD")
DATABASE_HOST = get_env_variable("DATABASE_HOST")
DATABASE_PORT = get_env_variable("DATABASE_PORT")
DATABASE_DB = get_env_variable("DATABASE_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = "%s://%s:%s@%s:%s/%s" % (
    DATABASE_DIALECT,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_DB,
)

# ----------------------------------------------------
# CELERY CONFIG
# ----------------------------------------------------
REDIS_HOST = get_env_variable("REDIS_HOST")
REDIS_PORT = get_env_variable("REDIS_PORT")
REDIS_DIALECT = get_env_variable("REDIS_DIALECT", "redis")
REDIS_CELERY_DB = get_env_variable("REDIS_CELERY_DB", "5")
REDIS_RESULTS_DB = get_env_variable("REDIS_RESULTS_DB", "6")

RESULTS_BACKEND = RedisCache(
    host=REDIS_HOST, port=REDIS_PORT, key_prefix="superset_results"
)


class CeleryConfig(object):
    BROKER_URL = f"{REDIS_DIALECT}://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    CELERY_IMPORTS = ("superset.sql_lab", "superset.tasks")
    CELERY_RESULT_BACKEND = (
        f"{REDIS_DIALECT}://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    )
    CELERYD_LOG_LEVEL = "DEBUG"
    CELERYD_PREFETCH_MULTIPLIER = 1
    CELERY_ACKS_LATE = False
    CELERYBEAT_SCHEDULE = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

# ----------------------------------------------------
# CACHE CONFIG
# https://superset.apache.org/docs/installation/cache/
# ----------------------------------------------------
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,  # 60 seconds * 60 minutes * 24 hours
    "CACHE_KEY_PREFIX": "superset_metadata_",
    "CACHE_REDIS_URL": f"{REDIS_DIALECT}://{REDIS_HOST}:{REDIS_PORT}/7",
}

FILTER_STATE_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_filter_",
    "CACHE_REDIS_URL": f"{REDIS_DIALECT}://{REDIS_HOST}:{REDIS_PORT}/8",
}

EXPLORE_FORM_DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_form_",
    "CACHE_REDIS_URL": f"{REDIS_DIALECT}://{REDIS_HOST}:{REDIS_PORT}/9",
}

DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "SupersetMetastoreCache",
    "CACHE_KEY_PREFIX": "superset_data_",
    "CACHE_DEFAULT_TIMEOUT": 86400,
}

# ----------------------------------------------------
# AUTHENTICATION CONFIG
# http://flask-appbuilder.readthedocs.io/en/latest/security.html#authentication-methods
# ----------------------------------------------------
# Dev: Use AUTH_DB i.e. user/pass authentication
AUTH_TYPE = AUTH_DB
# Production: Use OAUTH i.e. Google, Facebook, GitHub authentication
# AUTH_TYPE = AUTH_OAUTH
# Allow user self registration
# AUTH_USER_REGISTRATION = True
# The default user self registration role
# This role will be given in addition to any AUTH_ROLES_MAPPING
AUTH_USER_REGISTRATION_ROLE = "Public"
# If we should replace ALL the user's roles each login, or only on registration
AUTH_ROLES_SYNC_AT_LOGIN = True
# A mapping from the values of `userinfo["role_keys"]` to a list of FAB roles
AUTH_ROLES_MAPPING = {
    "User": ["Alpha"],
    "Admin": ["Admin"],
}

# Grant public role the same set of permissions as for a selected builtin role.
# This is use to enable anonymous users to view dashboards. Explicit grant on specific datasets is still required.
# https://superset.apache.org/docs/security/#public
PUBLIC_ROLE_LIKE = "Gamma"

# Enable Google and Github OAuth
OAUTH_PROVIDERS = [
    # {
    #     "name": "google",
    #     "icon": "fa-google",
    #     "token_key": "access_token",
    #     "remote_app": {
    #         "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    #         "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
    #         "api_base_url": "https://www.googleapis.com/oauth2/v2/",
    #         "client_kwargs": {"scope": "email profile"},
    #         "request_token_url": None,
    #         "access_token_url": "https://accounts.google.com/o/oauth2/token",
    #         "authorize_url": "https://accounts.google.com/o/oauth2/auth",
    #         "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
    #     },
    #     # "whitelist": ["@{}".format(os.getenv("GOOGLE_DOMAIN"))],
    # },
    {
        "name": "github",
        "icon": "fa-github",
        "token_key": "access_token",
        "remote_app": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "api_base_url": "https://api.github.com",
            "client_kwargs": {"scope": "read:user, read:org"},
            "access_token_url": "https://github.com/login/oauth/access_token",
            "authorize_url": "https://github.com/login/oauth/authorize",
            "request_token_url": None,
        },
    },
]

CUSTOM_SECURITY_MANAGER = CustomSsoSecurityManager

# ----------------------------------------------------
# ADDITIONAL CONFIGURATION
# ----------------------------------------------------
ENABLE_PROXY_FIX = True
ROW_LIMIT = 5000
# Enable Flask-WTF flag for CSRF
WTF_CSRF_ENABLED = True
SECRET_KEY = get_env_variable("SECRET_KEY", "my_precious")
FEATURE_FLAGS = {"ALERT_REPORTS": True}
ALERT_REPORTS_NOTIFICATION_DRY_RUN = True
WEBDRIVER_BASEURL = "http://superset:8088/"
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = WEBDRIVER_BASEURL
SQLLAB_CTAS_NO_LIMIT = True
