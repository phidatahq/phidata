"""Write-ownership check shared by the Company routers."""

from typing import Any, Dict, Optional

from fastapi import HTTPException


def _require_write_ownership(existing: Dict[str, Any], user_id: Optional[str], kind: str = "product") -> None:
    """Refuse a scoped caller writing to a Company record it does not own.

    Company reads are company-wide, so the row is always visible; a scoped caller
    that is not the owner gets an honest 403 rather than a 404. An unscoped caller
    (isolation off, or admin) may write to any record. Pass
    ``get_scoped_user_id(request)`` as ``user_id``.
    """
    if user_id is None:
        return
    owner = existing.get("user_id")
    if owner is None:
        raise HTTPException(status_code=403, detail=f"Cannot modify unowned {kind}")
    if owner != user_id:
        raise HTTPException(status_code=403, detail=f"Cannot modify {kind} owned by another user")
