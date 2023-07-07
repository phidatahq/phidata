from typing import List, Optional

import json
from httpx import Client, Response, NetworkError, codes

from phiterm.api.routes import ApiRoutes
from phiterm.api.handler import invalid_response
from phiterm.conf.constants import BACKEND_API_URL
from phiterm.schemas.user import UserSchema
from phiterm.schemas.workspace import WorkspaceSchema, WorkspaceActionData
from phiterm.utils.cli_console import log_network_error_msg
from phiterm.utils.log import logger


def parse_ws_response(
    resp: Response,
) -> Optional[WorkspaceSchema]:
    ws_dict = resp.json()
    if ws_dict is None or not isinstance(ws_dict, dict):
        logger.debug(f"Could not parse ws: {ws_dict}")
        return None

    # logger.debug("url: {}".format(resp.url))
    # logger.debug("status: {}".format(resp.status_code))
    # logger.debug("response: {}".format(resp.json()))

    if resp.status_code == codes.OK:
        return WorkspaceSchema.parse_obj(ws_dict)

    return None


def workspace_ping() -> bool:
    from phiterm.api.client import base_headers

    logger.debug("--o-o-- Pinging workspace api")

    with Client(base_url=BACKEND_API_URL, headers=base_headers, timeout=60) as api:
        try:
            r: Response = api.get(ApiRoutes.WORKSPACE_PING)
            if invalid_response(r):
                return False
        except NetworkError as e:
            log_network_error_msg()
            return False

        logger.debug("status: {}".format(r.status_code))
        logger.debug("headers: {}".format(r.headers))
        logger.debug("cookies: {}".format(r.cookies))
        logger.debug("url: {}".format(r.url))
        logger.debug("json: {}".format(r.json()))
        if r.status_code == codes.OK:
            return True

    return False


def get_primary_workspace(user: UserSchema) -> Optional[WorkspaceSchema]:
    from phiterm.api.client import get_authenticated_client

    logger.debug("--o-o-- Get primary workspace")

    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            r: Response = api.post(
                ApiRoutes.WORKSPACE_READ_PRIMARY, data=user.json(exclude_none=True)  # type: ignore
            )
            if invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        return parse_ws_response(r)


def get_available_workspaces(user: UserSchema) -> Optional[List[WorkspaceSchema]]:
    from phiterm.api.client import get_authenticated_client

    logger.debug("--o-o-- Get available workspaces")

    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            r: Response = api.post(
                ApiRoutes.WORKSPACES_READ_AVAILABLE, data=user.json(exclude_none=True)  # type: ignore
            )
            if invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        ws_list_dict = r.json()
        if ws_list_dict is None or not isinstance(ws_list_dict, list):
            logger.debug("No workspaces received")
            return []

        # convert ws_list_dict to List[WorkspaceSchema] and return
        if r.status_code == codes.OK:
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
    from phiterm.api.client import get_authenticated_client

    logger.debug("--o-o-- Create workspace")

    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            body = {
                "workspace_data": workspace.dict(exclude_none=True),
                "user_data": user.dict(exclude_none=True),
            }
            body_json = json.dumps(body)
            # logger.debug(f"body_json: {body_json})")
            r: Response = api.post(ApiRoutes.WORKSPACE_CREATE, json=body)
            if invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        return parse_ws_response(r)


def update_workspace(
    user: UserSchema,
    workspace: WorkspaceSchema,
) -> Optional[WorkspaceSchema]:
    from phiterm.api.client import get_authenticated_client

    logger.debug("--o-o-- Update workspace")

    authenticated_client = get_authenticated_client()
    if authenticated_client is None:
        return None

    with authenticated_client as api:
        try:
            body = {
                "workspace_data": workspace.dict(exclude_none=True),
                "user_data": user.dict(exclude_none=True),
            }
            body_json = json.dumps(body)
            # logger.debug(f"body_json: {body_json})")
            r: Response = api.post(ApiRoutes.WORKSPACE_UPDATE, json=body)
            if invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        return parse_ws_response(r)


def update_primary_workspace(
    user: UserSchema,
    workspace: WorkspaceSchema,
) -> Optional[WorkspaceSchema]:
    from phiterm.api.client import get_authenticated_client

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
                "user_data": user.dict(exclude_none=True),
            }
            body_json = json.dumps(body)
            # logger.debug(f"body_json: {body_json})")
            r: Response = api.post(ApiRoutes.WORKSPACE_UPDATE_PRIMARY, json=body)
            if invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        return parse_ws_response(r)


def delete_workspaces_api(
    user: Optional[UserSchema],
    workspaces_to_delete: List[str],
) -> bool:
    from phiterm.api.client import get_authenticated_client

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
                "user_data": user.dict(exclude_none=True),
            }
            body_json = json.dumps(body)
            logger.debug(f"body_json: {body_json})")
            r: Response = api.post(ApiRoutes.WORKSPACE_DELETE, json=body)
            if invalid_response(r):
                return False
        except NetworkError:
            log_network_error_msg()
            return False

    return True
