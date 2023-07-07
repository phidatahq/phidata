from dataclasses import dataclass
from typing import Optional


@dataclass
class ApiRoutes:
    # user paths
    USER_PING: str = "v1/user/ping"
    USER_READ: str = "v1/user/read"
    USER_UPDATE: str = "v1/user/update"
    USER_SIGN_IN: str = "v1/user/signin"
    USER_CLI_AUTH: str = "v1/user/cliauth"
    USER_AUTHENTICATE: str = "v1/user/authenticate"
    USER_AUTH_REFRESH: str = "v1/user/authrefresh"

    # workspace paths
    WORKSPACE_PING: str = "v1/workspace/ping"
    WORKSPACE_CREATE: str = "v1/workspace/create"
    WORKSPACE_UPDATE: str = "v1/workspace/update"
    WORKSPACE_DELETE: str = "v1/workspace/delete"
    WORKSPACE_UPDATE_PRIMARY: str = "v1/workspace/update/primary"
    WORKSPACE_READ_PRIMARY: str = "v1/workspace/read/primary"
    WORKSPACES_READ_AVAILABLE: str = "v1/workspace/read/available"
