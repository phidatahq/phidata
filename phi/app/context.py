from typing import Optional

from pydantic import BaseModel

from phi.api.schemas.workspace import WorkspaceSchema


class ContainerContext(BaseModel):
    workspace_name: Optional[str] = None
    # Path to the workspace root directory
    workspace_root: Optional[str] = None
    # Path to the parent directory of the workspace root
    workspace_parent: Optional[str] = None
    scripts_dir: Optional[str] = None
    storage_dir: Optional[str] = None
    workflows_dir: Optional[str] = None
    workspace_dir: Optional[str] = None
    workspace_schema: Optional[WorkspaceSchema] = None
    requirements_file: Optional[str] = None
