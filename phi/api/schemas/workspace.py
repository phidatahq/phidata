from typing import Any, Dict, Optional

from pydantic import BaseModel


class WorkspaceSchema(BaseModel):
    """
    Schema for workspace returned by API.
    """

    ws_name: Optional[str] = None
    id_user: Optional[int] = None
    id_workspace: Optional[int] = None
    visibility: Optional[str] = None
    ws_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_primary_ws_for_user: Optional[bool] = None
