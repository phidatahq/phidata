from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from agno.os.routers.agents import sandbox


@pytest.mark.asyncio
@pytest.mark.parametrize("durable, serializes_sessions", [(False, True), (True, False), (True, None)])
async def test_sandbox_submission_requires_durable_session_admission(durable, serializes_sessions):
    worker = SimpleNamespace(
        config=SimpleNamespace(durable=durable, redis=None),
        store=SimpleNamespace(serializes_sessions=serializes_sessions),
    )
    with pytest.raises(
        ValueError, match="^Sandbox API execution requires a durable queue with shared session admission$"
    ):
        await sandbox.enqueue_sandbox_run(Mock(), worker, input="hello", session_id="session", user_id=None, kwargs={})


@pytest.mark.asyncio
@pytest.mark.parametrize("redis", [None, "redis://localhost"])
async def test_replica_local_notice_is_info_once_and_only_without_redis(monkeypatch, redis):
    from agno.sandbox import _harness

    agent = Mock()
    agent.get_id.return_value = "coder"
    worker = SimpleNamespace(
        config=SimpleNamespace(durable=True, redis=redis, max_attempts=1, deployment_id=None),
        store=SimpleNamespace(serializes_sessions=True),
        _aresolve_job_component=AsyncMock(return_value=agent),
    )
    monkeypatch.setattr(_harness, "submission", Mock(return_value={}))
    monkeypatch.setattr(_harness, "acheck_tables", AsyncMock())
    monkeypatch.setattr(sandbox, "_session_owner", AsyncMock(return_value=None))
    monkeypatch.setattr(sandbox, "aenqueue_ticket", AsyncMock(return_value={"reason": "accepted"}))
    monkeypatch.setattr(sandbox, "aprepare_accepted_or_abort", AsyncMock())
    monkeypatch.setattr("agno.os.event_streams.get_event_stream", Mock(return_value=AsyncMock()))
    info = Mock()
    monkeypatch.setattr(sandbox, "log_info", info)
    sandbox._log_replica_local_coordination.cache_clear()
    try:
        for _ in range(2):
            await sandbox.enqueue_sandbox_run(
                agent, worker, input="hello", session_id="session", user_id=None, kwargs={}
            )
        if redis is None:
            info.assert_called_once_with(
                "Sandbox run streams and cancellation are replica-local; "
                "configure queue.redis for cross-replica streaming and cancellation."
            )
        else:
            info.assert_not_called()
    finally:
        sandbox._log_replica_local_coordination.cache_clear()
