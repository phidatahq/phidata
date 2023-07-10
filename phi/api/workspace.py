from typing import List, Optional

import json
from httpx import Client, Response, NetworkError

from phi.api.client import base_headers, get_authenticated_client
from phi.api.helpers import is_valid_response, is_invalid_response
from phi.api.routes import ApiRoutes
from phi.cli.console import log_network_error_msg
from phi.cli.settings import phi_cli_settings
from phi.schemas.user import UserSchema
from phi.schemas.workspace import WorkspaceSchema
from phi.utils.log import logger


def parse_ws_response(
    resp: Response,
) -> Optional[WorkspaceSchema]:
    ws_dict = resp.json()
    if ws_dict is None or not isinstance(ws_dict, dict):
        logger.debug(f"Could not parse workspace: {ws_dict}")
        return None

    logger.debug("url: {}".format(resp.url))
    logger.debug("status: {}".format(resp.status_code))
    logger.debug("response: {}".format(resp.json()))

    if is_valid_response(resp):
        return WorkspaceSchema.model_validate(ws_dict)

    return None


def workspace_ping() -> bool:
    logger.debug("--o-o-- Pinging workspace api")
    with Client(base_url=phi_cli_settings.api_url, headers=base_headers, timeout=60) as api:
        try:
            r: Response = api.get(ApiRoutes.WORKSPACE_PING)
            if is_invalid_response(r):
                return False
        except NetworkError:
            log_network_error_msg()
            return False

        logger.debug("status: {}".format(r.status_code))
        logger.debug("headers: {}".format(r.headers))
        logger.debug("cookies: {}".format(r.cookies))
        logger.debug("url: {}".format(r.url))
        logger.debug("json: {}".format(r.json()))

        if is_valid_response(r):
            return True

    return False


def get_primary_workspace(user: UserSchema) -> Optional[WorkspaceSchema]:
    logger.debug("--o-o-- Get primary workspace")
    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            r: Response = api.post(
                ApiRoutes.WORKSPACE_READ_PRIMARY, data=user.model_dump_json(exclude_none=True)  # type: ignore
            )
            if is_invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        return parse_ws_response(r)


def get_available_workspaces(user: UserSchema) -> Optional[List[WorkspaceSchema]]:
    logger.debug("--o-o-- Get available workspaces")
    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            r: Response = api.post(ApiRoutes.WORKSPACES_READ_AVAILABLE, data=user.model_dump(exclude_none=True))
            if is_invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        ws_list_dict = r.json()
        if ws_list_dict is None or not isinstance(ws_list_dict, list):
            logger.debug("No workspaces received")
            return []

        # convert ws_list_dict to List[WorkspaceSchema] and return
        if is_valid_response(r):
            ws_list: List[WorkspaceSchema] = []
            for ws_dict in ws_list_dict:
                if not isinstance(ws_dict, dict):
                    logger.debug("Could not parse {}".format(ws_dict))
                    continue
                ws_list.append(WorkspaceSchema.parse_obj(ws_dict))
            return ws_list

    return None


def create_workspace(
    user: UserSchema,
    workspace: WorkspaceSchema,
) -> Optional[WorkspaceSchema]:
    logger.debug("--o-o-- Create workspace")
    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            body = {
                "workspace_data": workspace.model_dump(exclude_none=True),
                "user_data": user.model_dump(exclude_none=True),
            }
            body_json = json.dumps(body)
            logger.debug(f"body: {body_json})")
            r: Response = api.post(ApiRoutes.WORKSPACE_CREATE, json=body)
            if is_invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        return parse_ws_response(r)


def update_workspace(
    user: UserSchema,
    workspace: WorkspaceSchema,
) -> Optional[WorkspaceSchema]:
    logger.debug("--o-o-- Update workspace")
    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            body = {
                "workspace_data": workspace.model_dump(exclude_none=True),
                "user_data": user.model_dump(exclude_none=True),
            }
            body_json = json.dumps(body)
            logger.debug(f"body_json: {body_json})")
            r: Response = api.post(ApiRoutes.WORKSPACE_UPDATE, json=body)
            if is_invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        return parse_ws_response(r)


def update_primary_workspace(
    user: UserSchema,
    workspace: WorkspaceSchema,
) -> Optional[WorkspaceSchema]:
    logger.debug(f"--o-o-- Update primary workspace to: {workspace.ws_name}")
    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            body = {
                "workspace_data": {
                    "update_primary_ws_id": workspace.id_workspace,
                    "update_primary_ws_name": workspace.ws_name,
                },
                "user_data": user.model_dump(exclude_none=True),
            }
            body_json = json.dumps(body)
            logger.debug(f"body_json: {body_json})")
            r: Response = api.post(ApiRoutes.WORKSPACE_UPDATE_PRIMARY, json=body)
            if is_invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        return parse_ws_response(r)


def delete_workspaces_api(
    user: Optional[UserSchema],
    workspaces_to_delete: List[str],
) -> bool:
    logger.debug("--o-o-- Deleting workspaces")
    if user is None:
        logger.error("User invalid")
        return False

    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return False

    with authenticated_client as api:
        try:
            body = {
                "workspaces": workspaces_to_delete,
                "user_data": user.model_dump(exclude_none=True),
            }
            body_json = json.dumps(body)
            logger.debug(f"body_json: {body_json})")
            r: Response = api.post(ApiRoutes.WORKSPACE_DELETE, json=body)
            if is_invalid_response(r):
                return False
        except NetworkError:
            log_network_error_msg()
            return False

    return True
