from typing import List, Optional

from phi.api.client import api_client, invalid_respose
from phi.api.routes import ApiRoutes
from phi.api.schemas.user import UserSchema
from phi.api.schemas.workspace import WorkspaceSchema
from phi.utils.log import logger


async def get_primary_workspace(user: UserSchema) -> Optional[WorkspaceSchema]:
    logger.debug("--o-o-- Get primary workspace")
    async with api_client.AuthenticatedSession() as api:
        async with api.post(
            ApiRoutes.WORKSPACE_READ_PRIMARY, json=user.model_dump(include={"id_user", "email"})
        ) as response:
            if invalid_respose(response):
                return None

            response_json = await response.json()
            if response_json is None:
                return None

            primary_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
            if primary_workspace is not None:
                return primary_workspace
            return None


async def get_available_workspaces(user: UserSchema) -> Optional[List[WorkspaceSchema]]:
    logger.debug("--o-o-- Get available workspaces")
    async with api_client.AuthenticatedSession() as api:
        async with api.post(
            ApiRoutes.WORKSPACE_READ_AVAILABLE, json=user.model_dump(include={"id_user", "email"})
        ) as response:
            if invalid_respose(response):
                return None

            response_json = await response.json()
            if response_json is None:
                return None

            available_workspaces: List[WorkspaceSchema] = []
            for workspace in response_json:
                if not isinstance(workspace, dict):
                    logger.debug("Could not parse {}".format(workspace))
                    continue
                available_workspaces.append(WorkspaceSchema.model_validate(workspace))
            return available_workspaces
