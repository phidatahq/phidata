from typing import Optional

from pydantic import BaseModel

from agno.api.schemas.workspace import WorkspaceSchema


class InfraContext(BaseModel):
    """InfraContext is a context object passed when creating Infra resources."""

    workspace_name: str
    # Path to the workspace directory inside the container
    workspace_root: str
    # Path to the workspace parent directory inside the container
    workspace_parent: str
    workspace_schema: Optional[WorkspaceSchema] = None
    requirements_file: Optional[str] = None
