"""Session ordering for jobs whose component requires one active turn at a time."""

from typing import Any, Dict, Iterable


def session_identity(job: Dict[str, Any]) -> tuple:
    # User/deployment affinity does not create a different mutable component session.
    return job.get("component_type"), job.get("component_id"), job.get("session_id")


def session_blocked(job: Dict[str, Any], others: Iterable[Dict[str, Any]]) -> bool:
    if (job.get("payload") or {}).get("serialize_session") is not True:
        return False
    order = (job["created_at"], job["id"])
    for other in others:
        if other["id"] == job["id"] or session_identity(other) != session_identity(job):
            continue
        if (other.get("payload") or {}).get("serialize_session") is not True:
            continue
        if other["status"] == "running":
            return True
        if job["status"] == "queued" and other["status"] == "queued" and (other["created_at"], other["id"]) < order:
            return True
    return False


def session_claim_condition(table: Any) -> Any:
    """SQL equivalent of session_blocked, evaluated before claiming a Postgres ticket."""
    from sqlalchemy import and_, exists, or_, select

    other = table.alias("session_predecessor")
    serialized = table.c.payload.contains({"serialize_session": True})
    other_serialized = other.c.payload.contains({"serialize_session": True})
    earlier = or_(
        other.c.created_at < table.c.created_at,
        and_(other.c.created_at == table.c.created_at, other.c.id < table.c.id),
    )
    blocker = (
        select(other.c.id)
        .where(
            other.c.id != table.c.id,
            other.c.component_type == table.c.component_type,
            other.c.component_id == table.c.component_id,
            other.c.session_id == table.c.session_id,
            other_serialized,
            or_(
                other.c.status == "running",
                and_(table.c.status == "queued", other.c.status == "queued", earlier),
            ),
        )
        .correlate(table)
    )
    return or_(~serialized, ~exists(blocker))


def session_claim_lock_key(namespace: str, job: Dict[str, Any]) -> int:
    """A stable Postgres advisory-lock key scoped to one queue and component session."""
    import hashlib
    import json

    value = json.dumps((namespace, session_identity(job)), separators=(",", ":"))
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big", signed=True)
