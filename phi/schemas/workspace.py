from typing import Any, Dict, Optional

from pydantic import BaseModel


class WorkspaceSchema(BaseModel):
    """
    Schema for user workspace used by API.
    """

    ws_name: Optional[str] = None
    id_user: Optional[int] = None
    id_workspace: Optional[int] = None
    is_primary_ws_for_user: Optional[bool] = None
    visibility: Optional[str] = None
    ws_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_test: Optional[bool] = None


class WorkspaceActionData(BaseModel):
    """
    Schema for workspace action data.
    """

    id_user: int
    id_workspace: int
    action: str
    action_data: Optional[Dict[str, Any]] = None
