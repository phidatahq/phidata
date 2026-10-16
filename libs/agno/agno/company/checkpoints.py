"""Open a completed executor run's committed checkpoint on the host."""

from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Iterator

from agno.sandbox.checkpoint import CheckpointRef, CheckpointStore


def _checkpoint_store(agent: Any) -> CheckpointStore:
    # Replace this private coordinator import with the public checkpoint surface when available.
    from agno.sandbox._harness import coordinator

    return coordinator(agent).transfer.store


def _reference(agent: Any, run: Any) -> CheckpointRef:
    row = run if isinstance(run, dict) else run.to_dict()
    data = row.get("run_data") or row
    if row.get("agent_id", data.get("agent_id")) != agent.id:
        raise ValueError("Checkpoint run belongs to another agent")
    status = row.get("status", data.get("status"))
    if getattr(status, "value", status) != "COMPLETED":
        raise ValueError("Checkpoint run must be COMPLETED")
    reference = (data.get("metadata") or {}).get("sandbox", {}).get("checkpoint")
    if not isinstance(reference, dict):
        raise ValueError("Run has no committed checkpoint")
    return CheckpointRef(**reference)


@asynccontextmanager
async def open_run_checkpoint(agent: Any, run: Any) -> AsyncIterator[Path]:
    """Yield the verified archive for this agent's completed run, until context exit."""
    reference = _reference(agent, run)
    store = _checkpoint_store(agent)
    async with store.aopen_archive(reference) as path:
        yield path


@contextmanager
def open_run_checkpoint_sync(agent: Any, run: Any) -> Iterator[Path]:
    """Synchronous twin of :func:`open_run_checkpoint`."""
    reference = _reference(agent, run)
    store = _checkpoint_store(agent)
    with store.open_archive(reference) as path:
        yield path
