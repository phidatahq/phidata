"""The sandbox duplicate-key branch uses the shared component check, so it refuses the same keys as the agent and team routes.

Only the queue store is replaced (it returns the stored original); ``enqueue_sandbox_run`` and the shared
``ensure_duplicate_matches_component`` are real. The wiring with real Redis/Postgres is in the sandbox integration tests.
"""

from types import SimpleNamespace
from typing import Any, Dict

import pytest
from fastapi import HTTPException

from agno.os.job_queue import queue_scope
from agno.os.routers.agents.sandbox import enqueue_sandbox_run


class _Agent:
    def get_id(self) -> str:
        return "coder"


def _worker(original: Dict[str, Any], agent: _Agent) -> SimpleNamespace:
    async def enqueue_job(job: Dict[str, Any], max_depth: Any = None) -> Dict[str, Any]:
        return {"reason": "duplicate", "job": original}

    async def resolve(_: Dict[str, Any]) -> _Agent:
        return agent

    store = SimpleNamespace(enqueue_job=enqueue_job, serializes_sessions=True)
    config = SimpleNamespace(durable=True, redis=object(), max_attempts=3, deployment_id=None, max_queue_depth=10)
    return SimpleNamespace(store=store, config=config, _aresolve_job_component=resolve)


def _original(**overrides: Any) -> Dict[str, Any]:
    original = {
        "id": "original-run",
        "component_type": "agent",
        "component_id": "coder",
        "session_id": "s1",
        "user_id": None,
        "payload": {"input": "hello", "kwargs": {}, "stream": True, "serialize_session": True, "session_seq": 7},
    }
    original.update(overrides)
    return original


async def _retry(original: Dict[str, Any], **overrides: Any) -> Dict[str, Any]:
    agent = _Agent()
    submission = dict(input="hello", session_id="s1", user_id=None, kwargs={}, idempotency_key="k")
    submission.update(overrides)
    return await enqueue_sandbox_run(agent, _worker(original, agent), **submission)


@pytest.fixture(autouse=True)
def _no_harness_validation(monkeypatch):
    # The submission checks need a real sandboxed agent; they run before the queue and are not what is tested here.
    import sys
    import types

    from agno import sandbox

    stub = types.SimpleNamespace(submission=lambda agent, input, kwargs: dict(kwargs))
    monkeypatch.setitem(sys.modules, "agno.sandbox._harness", stub)
    monkeypatch.setattr(sandbox, "_harness", stub, raising=False)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [{}, {"input": "changed"}, {"session_id": "another-session"}],
    ids=["identical", "changed-input", "another-session"],
)
async def test_a_duplicate_returns_the_original_ticket_with_queue_fields_in_its_payload(overrides):
    original = _original()
    assert await _retry(original, **overrides) is original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "original",
    [
        _original(component_type="team"),
        _original(component_id="another-agent"),
        _original(payload={"input": "hello", "scope": queue_scope(None, 3, pinned=3)}),
    ],
    ids=["other-type", "other-id", "pinned-version"],
)
async def test_a_key_from_another_component_type_id_or_pinned_version_is_refused(original):
    with pytest.raises(HTTPException) as refused:
        await _retry(original)
    assert refused.value.status_code == 409 and "different component" in refused.value.detail
    assert "another-agent" not in refused.value.detail and "original-run" not in refused.value.detail


@pytest.mark.asyncio
async def test_a_duplicate_whose_original_cannot_be_read_is_refused():
    async def enqueue_job(job, max_depth=None):
        return {"reason": "duplicate", "job": None}

    agent = _Agent()
    worker = _worker(_original(), agent)
    worker.store.enqueue_job = enqueue_job
    with pytest.raises(HTTPException) as refused:
        await enqueue_sandbox_run(agent, worker, input="hello", session_id="s1", user_id=None, kwargs={})
    assert refused.value.status_code == 409
