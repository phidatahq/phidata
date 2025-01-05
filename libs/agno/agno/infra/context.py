from typing import Optional

from pydantic import BaseModel

from agno.api.schemas.workspace import WorkspaceSchema


class InfraContext(BaseModel):
    """InfraContext is a context object passed when creating Infra resources."""

    # Workspace name
    workspace_name: str
    # Workspace schema from the API
    workspace_schema: Optional[WorkspaceSchema] = None

    # -*- Container context
    # Path to the workspace directory inside the container
    workspace_root: str
    # Path to the workspace parent directory inside the container
    workspace_parent: str
    # Path to the requirements.txt file relative to the workspace_root
    requirements_file: Optional[str] = None
