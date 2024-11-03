from typing import List, Optional, Dict

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.user import UserSchema
from phi.api.schemas.team import TeamSchema
from phi.utils.log import logger


def get_teams_for_user(user: UserSchema) -> Optional[List[TeamSchema]]:
    logger.debug("--**-- Reading teams for user")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.TEAM_READ_ALL,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                },
                timeout=2.0,
            )
            if invalid_response(r):
                return None

            response_json: Optional[List[Dict]] = r.json()
            if response_json is None:
                return None

            teams: List[TeamSchema] = [TeamSchema.model_validate(team) for team in response_json]
            return teams
        except Exception as e:
            logger.debug(f"Could not read teams: {e}")
    return None
