"""Validation and explicit lifecycle rules for Company tasks."""

import time
from typing import Any, Dict, Optional

TASK_TRANSITIONS = {
    "backlog": {"ready", "cancelled"},
    "ready": {"cancelled", "in_progress", "backlog"},
    "in_progress": {"in_review", "cancelled", "backlog"},
    "in_review": {"cancelled", "done", "in_progress", "backlog"},
    "done": set(),
    "cancelled": set(),
}


def validate_task_fields(fields: Dict[str, Any]) -> None:
    """Identity, acceptance and lifecycle are never descriptive edits."""
    unknown = set(fields) - {"title", "brief", "project_id"}
    if unknown:
        raise ValueError(f"Unsupported task fields: {sorted(unknown)}")
    if "title" in fields and (not isinstance(fields["title"], str) or not fields["title"].strip()):
        raise ValueError("title must be a non-empty string")
    if fields.get("brief") is not None and not isinstance(fields["brief"], str):
        raise ValueError("brief must be a string or None")
    if fields.get("project_id") is not None and (
        not isinstance(fields["project_id"], str) or not fields["project_id"].strip()
    ):
        raise ValueError("project_id must be a non-empty string or None")


def task_transition_fields(
    existing: Dict[str, Any],
    target: str,
    reason: str,
    accepted_by: Optional[str] = None,
    executor_type: Optional[str] = None,
    executor_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build lifecycle fields after validating a transition; callers persist atomically."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("A transition requires a non-empty reason")
    if target not in TASK_TRANSITIONS.get(existing["status"], set()):
        raise ValueError(f"Invalid task transition from {existing['status']} to {target}")
    now = int(time.time())
    fields: Dict[str, Any] = {"status": target, "updated_at": now}
    if target == "ready":
        if (
            executor_type not in {"agent", "team", "workflow", "engineering"}
            or not isinstance(executor_id, str)
            or not executor_id.strip()
        ):
            raise ValueError("Ready requires an executor type and id")
        fields.update(executor_type=executor_type, executor_id=executor_id, accepted_by=accepted_by, accepted_at=now)
    elif executor_type is not None or executor_id is not None:
        raise ValueError("Only Ready can set an executor")
    if target == "backlog":
        fields.update(executor_type=None, executor_id=None, accepted_by=None, accepted_at=None)
    fields["transitions"] = [
        *(existing.get("transitions") or []),
        {"from": existing["status"], "target": target, "reason": reason, "user_id": accepted_by, "created_at": now},
    ]
    return fields
