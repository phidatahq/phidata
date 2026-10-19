"""Component capacity enforced by queue stores across workers and deployments."""

from typing import Any, Dict, Iterable, Optional


def _validate_capacity(value: Optional[int]) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
        raise ValueError("max_concurrent_runs must be a positive integer or None")


def _capacity_blocked(job: Dict[str, Any], others: Iterable[Dict[str, Any]]) -> bool:
    limit = (job.get("payload") or {}).get("max_concurrent_runs")
    if limit is None:
        return False
    _validate_capacity(limit)
    return (
        sum(
            other["id"] != job["id"]
            and other["status"] == "running"
            and other["component_type"] == job["component_type"]
            and other["component_id"] == job["component_id"]
            for other in others
        )
        >= limit
    )


def _capacity_condition(table: Any) -> Any:
    from sqlalchemy import Integer, func, or_, select

    other = table.alias("component_running")
    limit = table.c.payload["max_concurrent_runs"].astext.cast(Integer)
    running = (
        select(func.count())
        .select_from(other)
        .where(
            other.c.id != table.c.id,
            other.c.status == "running",
            other.c.component_type == table.c.component_type,
            other.c.component_id == table.c.component_id,
        )
        .correlate(table)
        .scalar_subquery()
    )
    return or_(limit.is_(None), running < limit)


def _capacity_lock_key(namespace: str, job: Dict[str, Any]) -> int:
    import hashlib
    import json

    value = json.dumps(("component-capacity", namespace, job["component_type"], job["component_id"]))
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big", signed=True)
