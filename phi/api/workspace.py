from typing import List, Optional, Dict, Union

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.user import UserSchema
from phi.api.schemas.workspace import (
    WorkspaceSchema,
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceDelete,
    WorkspaceEvent,
)
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


def create_workspace_for_user(user: UserSchema, workspace: WorkspaceCreate) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--**-- Create workspace")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.WORKSPACE_CREATE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            created_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
            if created_workspace is not None:
                return created_workspace
        except Exception as e:
            logger.debug(f"Could not create workspace: {e}")
    return None


def update_workspace_for_user(user: UserSchema, workspace: WorkspaceUpdate) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--**-- Update workspace")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.WORKSPACE_UPDATE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            updated_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
            if updated_workspace is not None:
                return updated_workspace
        except Exception as e:
            logger.debug(f"Could not update workspace: {e}")
    return None


def delete_workspace_for_user(user: UserSchema, workspace: WorkspaceDelete) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--**-- Delete workspace")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.WORKSPACE_DELETE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            updated_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
            if updated_workspace is not None:
                return updated_workspace
        except Exception as e:
            logger.debug(f"Could not delete workspace: {e}")
    return None


def log_workspace_event(user: UserSchema, workspace_event: WorkspaceEvent) -> bool:
    if not phi_cli_settings.api_enabled:
        return False

    logger.debug("--**-- Log workspace event")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.WORKSPACE_EVENT_CREATE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "event": workspace_event.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            if isinstance(response_json, dict) and response_json.get("status") == "success":
                return True
            return False
        except Exception as e:
            logger.debug(f"Could not log workspace event: {e}")
    return False
