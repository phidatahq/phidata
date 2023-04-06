import os
import logging
from typing import Any, List, Union

from airflow.configuration import conf
from airflow.www.fab_security.manager import AUTH_DB, AUTH_OAUTH
from airflow.www.security import AirflowSecurityManager

basedir = os.path.abspath(os.path.dirname(__file__))

# Enable Flask-WTF flag for CSRF
WTF_CSRF_ENABLED = True
CSRF_ENABLED = True

# The SQLAlchemy connection string
SQLALCHEMY_DATABASE_URI = conf.get("database", "SQL_ALCHEMY_CONN")

# ----------------------------------------------------
# AUTHENTICATION CONFIG
# ----------------------------------------------------
# For details on how to set up each of the following authentication, see
# http://flask-appbuilder.readthedocs.io/en/latest/security.html#authentication-methods

# The authentication types
# AUTH_OID : Is for OpenID
# AUTH_DB : Is for database
# AUTH_LDAP : Is for LDAP
# AUTH_REMOTE_USER : Is for using REMOTE_USER from web server
# AUTH_OAUTH : Is for OAuth

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
# Use the OauthAuthorizer class to authorize user roles
FAB_SECURITY_MANAGER_CLASS = "webserver_config.OauthAuthorizer"
# A mapping from the values of `userinfo["role_keys"]` to a list of FAB roles
AUTH_ROLES_MAPPING = {
    "User": ["User"],
    "Admin": ["Admin"],
}

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


def get_roles_for_email(email: str) -> List[str]:
    """Returns a list of roles for an email.
    When a user logs in using Google, the email is used to determine their role.
    This is useful for granting admin access to specific users.
    All other users will be granted the "User" role.
    """

    ADMIN_EMAILS: List[str] = []
    if email in ADMIN_EMAILS:
        return ["Admin"]
    else:
        return ["User"]


def get_roles_for_gh_team(team_payload: List[dict]) -> List[str]:
    """Returns a list of roles for a github team.
    When a user logs in using GitHub, the team payload is used to determine their role.
    This is useful for granting admin access to specific teams and user access to other teams.
    All other users will be granted the "Public" role.

    The team payload is a list of dicts with the following keys:
    - id: int
    - name: str
    - slug: str
    - privacy: str
    - organization: dict
    - url: str
    - html_url: str
    """

    ADMIN_TEAM_SLUGS = ["data-platform-admins"]
    USER_TEAM_SLUGS = ["data-platform-users"]

    team_slugs = [team["slug"] for team in team_payload]
    if any(team_slug in ADMIN_TEAM_SLUGS for team_slug in team_slugs):
        return ["Admin"]
    elif any(team_slug in USER_TEAM_SLUGS for team_slug in team_slugs):
        return ["User"]
    else:
        return ["Public"]


class OauthAuthorizer(AirflowSecurityManager):
    # For other providers:
    # https://github.com/dpgaspar/Flask-AppBuilder/blob/master/flask_appbuilder/security/manager.py#L550
    def get_oauth_user_info(
        self, provider: str, resp: Any
    ) -> dict[str, Union[str, list[str]]]:
        logging.info(f"Getting user info from {provider}")

        if provider == "google":
            userinfo = self.appbuilder.sm.oauth_remotes[provider].get("userinfo")

            user_data = userinfo.json()
            email = user_data.get("email", "")
            roles = get_roles_for_email(email)
            logging.info(f"User {email} has roles: {roles}")
            return {
                "username": "g_" + user_data.get("id", ""),
                "first_name": user_data.get("given_name", ""),
                "last_name": user_data.get("family_name", ""),
                "email": email,
                "role_keys": roles,
            }

        elif provider == "github":
            remote_app = self.appbuilder.sm.oauth_remotes[provider]

            user_data = remote_app.get("user").json()
            team_data = remote_app.get("user/teams").json()
            login = user_data.get("login")
            roles = get_roles_for_gh_team(team_data)
            logging.info(f"User {login} has roles: {roles}")
            return {"username": "gh_" + login, "role_keys": roles}

        else:
            return {}


# ----------------------------------------------------
# Theme CONFIG
# ----------------------------------------------------
# Flask App Builder comes up with a number of predefined themes
# that you can use for Apache Airflow.
# http://flask-appbuilder.readthedocs.io/en/latest/customizing.html#changing-themes
# Please make sure to remove "navbar_color" configuration from airflow.cfg
# in order to fully utilize the theme. (or use that property in conjunction with theme)
# APP_THEME = "bootstrap-theme.css"  # default bootstrap
# APP_THEME = "amelia.css"
# APP_THEME = "cerulean.css"
# APP_THEME = "cosmo.css"
# APP_THEME = "cyborg.css"
# APP_THEME = "darkly.css"
# APP_THEME = "flatly.css"
# APP_THEME = "journal.css"
# APP_THEME = "lumen.css"
# APP_THEME = "paper.css"
# APP_THEME = "readable.css"
# APP_THEME = "sandstone.css"
# APP_THEME = "simplex.css"
# APP_THEME = "slate.css"
# APP_THEME = "solar.css"
# APP_THEME = "spacelab.css"
# APP_THEME = "superhero.css"
# APP_THEME = "united.css"
# APP_THEME = "yeti.css"
