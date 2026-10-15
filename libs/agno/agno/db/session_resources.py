"""Guard conversation deletion while external session resources still need cleanup."""

from typing import Any, List, Optional


class SessionResourcesPending(ValueError):
    """Retire external resources before removing their durable ownership record."""


def sandbox_bindings_query(bindings: Any, namespace: str, session_ids: List[str], user_id: Optional[str]) -> Any:
    """Lock the sandbox bindings a session delete would cascade, before any session row."""
    from sqlalchemy import select

    query = select(bindings.c.record).where(bindings.c.namespace == namespace, bindings.c.session_id.in_(session_ids))
    if user_id is not None:
        query = query.where(bindings.c.user_id == user_id)
    return query.with_for_update()


def assert_session_resources_released(record: Any) -> None:
    if not isinstance(record, dict) or record.get("phase") == "deleted":
        return
    if record.get("phase") == "deleting" or any(
        record.get(key) for key in ("checkpoint", "staged_checkpoint", "published_checkpoints", "computer")
    ):
        raise SessionResourcesPending("Delete the session's sandbox recovery data before deleting conversation history")
