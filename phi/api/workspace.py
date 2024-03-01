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
    UpdatePrimaryWorkspace,
)
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


def get_primary_workspace(user: UserSchema) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Get primary workspace")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.WORKSPACE_READ_PRIMARY, json=user.model_dump(include={"id_user", "email"})
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            primary_workspace: WorkspaceSchema = WorkspaceSchema.model_validate(response_json)
            if primary_workspace is not None:
                return primary_workspace
        except Exception as e:
            logger.debug(f"Could not get primary workspace: {e}")
    return None


def get_available_workspaces(user: UserSchema) -> Optional[List[WorkspaceSchema]]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Get available workspaces")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.WORKSPACE_READ_AVAILABLE, json=user.model_dump(include={"id_user", "email"})
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            available_workspaces: List[WorkspaceSchema] = []
            for workspace in response_json:
                if not isinstance(workspace, dict):
                    logger.debug(f"Not a dict: {workspace}")
                    continue
                available_workspaces.append(WorkspaceSchema.model_validate(workspace))
            return available_workspaces
        except Exception as e:
            logger.debug(f"Could not get available workspaces: {e}")
    return None


def create_workspace_for_user(user: UserSchema, workspace: WorkspaceCreate) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Create workspace")
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

    logger.debug("--o-o-- Update workspace")
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


def update_primary_workspace_for_user(user: UserSchema, workspace: UpdatePrimaryWorkspace) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug(f"--o-o-- Update primary workspace to: {workspace.ws_name}")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.WORKSPACE_UPDATE_PRIMARY,
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
            logger.debug(f"Could not update primary workspace: {e}")
    return None


def delete_workspace_for_user(user: UserSchema, workspace: WorkspaceDelete) -> Optional[WorkspaceSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Delete workspace")
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

    logger.debug("--o-o-- Log workspace event")
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
