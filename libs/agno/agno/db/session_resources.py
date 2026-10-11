"""Guard conversation deletion while external session resources still need cleanup."""

from typing import Any


class SessionResourcesPending(ValueError):
    """Retire external resources before removing their durable ownership record."""


def assert_session_resources_released(data: Any) -> None:
    if not isinstance(data, dict):
        return
    incarnation = data.get("_sandbox_incarnation")
    if incarnation is not None and data.get("_sandbox_recovery_deleted") != incarnation:
        raise SessionResourcesPending("Delete the session's sandbox recovery data before deleting conversation history")
