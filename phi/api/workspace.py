from typing import List, Optional

from phi.api.client import api_client, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.user import UserSchema
from phi.api.schemas.workspace import (
    WorkspaceSchema,
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceDelete,
    WorkspaceEvent,
    UpdatePrimaryWorkspace,
)
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


async def get_primary_workspace(user: UserSchema) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Get primary workspace")
    try:
        async with api_client.AuthenticatedSession() as api:
            async with api.post(
                ApiRoutes.WORKSPACE_READ_PRIMARY, json=user.model_dump(include={"id_user", "email"})
            ) as response:
                if invalid_response(response):
                    return None

                response_json = await response.json()
                if response_json is None:
                    return None

                primary_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
                if primary_workspace is not None:
                    return primary_workspace
                return None
    except Exception as e:
        logger.debug(f"Could not get primary workspace: {e}")
    return None


async def get_available_workspaces(user: UserSchema) -> Optional[List[WorkspaceSchema]]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Get available workspaces")
    try:
        async with api_client.AuthenticatedSession() as api:
            async with api.post(
                ApiRoutes.WORKSPACE_READ_AVAILABLE, json=user.model_dump(include={"id_user", "email"})
            ) as response:
                if invalid_response(response):
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
    except Exception as e:
        logger.debug(f"Could not get available workspaces: {e}")
    return None


async def create_workspace_for_user(user: UserSchema, workspace: WorkspaceCreate) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Create workspace")
    try:
        async with api_client.AuthenticatedSession() as api:
            async with api.post(
                ApiRoutes.WORKSPACE_CREATE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            ) as response:
                if invalid_response(response):
                    return None

                response_json = await response.json()
                if response_json is None:
                    return None

                # logger.debug(f"response_json: {response_json}")
                created_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
                if created_workspace is not None:
                    return created_workspace
                return None
    except Exception as e:
        logger.debug(f"Could not create workspace for user: {e}")
    return None


async def update_workspace_for_user(user: UserSchema, workspace: WorkspaceUpdate) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Update workspace")
    try:
        async with api_client.AuthenticatedSession() as api:
            async with api.post(
                ApiRoutes.WORKSPACE_UPDATE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            ) as response:
                if invalid_response(response):
                    return None

                response_json = await response.json()
                if response_json is None:
                    return None

                updated_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
                if updated_workspace is not None:
                    return updated_workspace
    except Exception as e:
        logger.debug(f"Could not create anon user: {e}")
    return None


async def update_primary_workspace_for_user(
    user: UserSchema, workspace: UpdatePrimaryWorkspace
) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug(f"--o-o-- Update primary workspace to: {workspace.ws_name}")
    try:
        async with api_client.AuthenticatedSession() as api:
            async with api.post(
                ApiRoutes.WORKSPACE_UPDATE_PRIMARY,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            ) as response:
                if invalid_response(response):
                    return None

                response_json = await response.json()
                if response_json is None:
                    return None

                # logger.debug(f"response_json: {response_json}")
                updated_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
                if updated_workspace is not None:
                    return updated_workspace
                return None
    except Exception as e:
        logger.debug(f"Could not update primary workspace for user: {e}")
    return None


async def delete_workspace_for_user(user: UserSchema, workspace: WorkspaceDelete) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Delete workspace")
    try:
        async with api_client.AuthenticatedSession() as api:
            async with api.post(
                ApiRoutes.WORKSPACE_DELETE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            ) as response:
                if invalid_response(response):
                    return None

                response_json = await response.json()
                if response_json is None:
                    return None

                # logger.debug(f"response_json: {response_json}")
                updated_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
                if updated_workspace is not None:
                    return updated_workspace
                return None
    except Exception as e:
        logger.debug(f"Could not delete workspace for user: {e}")
    return None


async def log_workspace_event(user: UserSchema, workspace_event: WorkspaceEvent) -> bool:
    if not phi_cli_settings.api_enabled:
        return False

    logger.debug("--o-o-- Log workspace event")
    try:
        async with api_client.AuthenticatedSession() as api:
            async with api.post(
                ApiRoutes.WORKSPACE_EVENT,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "workspace_event": workspace_event.model_dump(exclude_none=True),
                },
            ) as response:
                if invalid_response(response):
                    return False

                response_json = await response.json()
                # logger.debug(f"response_json: {response_json}")
                if response_json is None:
                    return False

                if isinstance(response_json, dict) and response_json.get("status") == "success":
                    return True
                return False
    except Exception as e:
        logger.debug(f"Could not claim anonymous workspaces: {e}")
    return False
