import logging
from typing import List

from superset.security import SupersetSecurityManager


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


class CustomSsoSecurityManager(SupersetSecurityManager):
    # For other providers:
    # https://github.com/dpgaspar/Flask-AppBuilder/blob/master/flask_appbuilder/security/manager.py#L550
    def oauth_user_info(self, provider, response=None):
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
