from dataclasses import dataclass


@dataclass
class ApiRoutes:
    # user paths
    USER_HEALTH: str = "/v1/user/health"
    USER_READ: str = "/v1/user/read"
    USER_UPDATE: str = "/v1/user/update"
    USER_SIGN_IN: str = "/v1/user/signin"
    USER_CLI_AUTH: str = "/v1/user/cliauth"
    USER_AUTHENTICATE: str = "/v1/user/authenticate"
    USER_AUTH_REFRESH: str = "/v1/user/authrefresh"

    # workspace paths
    WORKSPACE_HEALTH: str = "/v1/workspace/health"
    WORKSPACE_CREATE: str = "/v1/workspace/create"
    WORKSPACE_UPDATE: str = "/v1/workspace/update"
    WORKSPACE_DELETE: str = "/v1/workspace/delete"
    WORKSPACE_UPDATE_PRIMARY: str = "/v1/workspace/update/primary"
    WORKSPACE_READ_PRIMARY: str = "/v1/workspace/read/primary"
    WORKSPACE_READ_AVAILABLE: str = "/v1/workspace/read/available"
