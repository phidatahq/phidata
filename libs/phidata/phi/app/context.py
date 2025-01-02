from typing import Optional

from pydantic import BaseModel

from phi.api.schemas.workspace import WorkspaceSchema


class ContainerContext(BaseModel):
    workspace_name: str
    # Path to the workspace directory inside the container
    workspace_root: str
    # Path to the workspace parent directory inside the container
    workspace_parent: str
    scripts_dir: Optional[str] = None
    storage_dir: Optional[str] = None
    workflows_dir: Optional[str] = None
    workspace_dir: Optional[str] = None
    workspace_schema: Optional[WorkspaceSchema] = None
    requirements_file: Optional[str] = None
