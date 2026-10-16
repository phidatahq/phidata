"""Validation and explicit lifecycle rules for Company projects."""

import time
from typing import Any, Dict, Optional

PROJECT_TRANSITIONS = {
    "proposed": {"cancelled", "active"},
    "active": {"cancelled", "done"},
    "done": set(),
    "cancelled": set(),
}


def validate_project_fields(fields: Dict[str, Any]) -> None:
    """Identity, acceptance and lifecycle are never descriptive edits."""
    unknown = set(fields) - {"target_date", "name", "outcome"}
    if unknown:
        raise ValueError(f"Unsupported project fields: {sorted(unknown)}")
    if "name" in fields and (not isinstance(fields["name"], str) or not fields["name"].strip()):
        raise ValueError("name must be a non-empty string")
    if fields.get("outcome") is not None and not isinstance(fields["outcome"], str):
        raise ValueError("outcome must be a string or None")
    if fields.get("target_date") is not None and (
        not isinstance(fields["target_date"], int) or isinstance(fields["target_date"], bool)
    ):
        raise ValueError("target_date must be epoch seconds or None")


def project_transition_fields(
    existing: Dict[str, Any],
    target: str,
    reason: str,
    accepted_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Build lifecycle fields after validating a transition; callers persist atomically."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("A transition requires a non-empty reason")
    if target not in PROJECT_TRANSITIONS.get(existing["status"], set()):
        raise ValueError(f"Invalid project transition from {existing['status']} to {target}")
    now = int(time.time())
    fields: Dict[str, Any] = {"status": target, "updated_at": now}
    fields["transitions"] = [
        *(existing.get("transitions") or []),
        {"from": existing["status"], "target": target, "reason": reason, "user_id": accepted_by, "created_at": now},
    ]
    return fields
