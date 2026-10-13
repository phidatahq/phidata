"""The relay: an always-present reader moving journal pages into the event stream, resumable by cursor."""

import asyncio
import json
from typing import Any, Dict, List

import pytest

from agno.os.event_streams.in_memory import InMemoryEventStream
from agno.run.base import RunStatus
from agno.sandbox import ExecResult, SandboxError, SandboxHandle
from agno.sandbox.relay import EventStreamRelaySink, MemoryRelayState, RelayedPage, SandboxRelay


def _handle(session_id: str, *, url: Any = "http://127.0.0.1:1", token: str = "t", state: str = "running"):
    return SandboxHandle("ref-" + session_id, "name", "coder", session_id, 1, state, "digest", url, token)


class FakeProvider:
    """Sandboxes whose runtimes serve scripted pages."""

    def __init__(self) -> None:
        self.handles: List[SandboxHandle] = []
        self.executions: Dict[str, List[Dict[str, Any]]] = {}
        self.pages: Dict[str, List[Dict[str, Any]]] = {}
        self.polls: List[Dict[str, Any]] = []
        self.health_error: Dict[str, str] = {}
        self.release = asyncio.Event()
        self.release.set()

    async def alist(self):
        return list(self.handles)

    async def ahealth(self, handle):
        if handle.session_id in self.health_error:
            raise SandboxError(self.health_error[handle.session_id])
        return {"version": 1, "ok": True, "executions": self.executions.get(handle.session_id, [])}

    async def arpc(self, handle, operation, payload):
        request = json.loads(payload)
        self.polls.append({"session": handle.session_id, **request})
        await self.release.wait()
        queue = self.pages.setdefault(request["execution_id"], [])
        if not queue:
            await asyncio.sleep(0.02)
            empty = {
                "version": 1,
                "execution_id": request["execution_id"],
                "cursor": request["cursor"],
                "frames": [],
                "result": None,
            }
            return ExecResult(0, json.dumps(empty), "")
        page = queue.pop(0)
        if page.get("fail"):
            return ExecResult(1, "", "runtime unavailable")
        return ExecResult(0, json.dumps({"version": 1, "execution_id": request["execution_id"], **page}), "")


def _event(content: str, run_id: str = "run-1") -> Dict[str, Any]:
    return {
        "type": "event",
        "event": {"event": "RunContent", "content": content, "run_id": run_id, "agent_id": "coder"},
    }


def _relay(provider: FakeProvider):
    stream, state = InMemoryEventStream(), MemoryRelayState()
    return SandboxRelay(provider, EventStreamRelaySink(state, event_stream=stream), sweep_interval=0.01), stream, state


@pytest.mark.asyncio
async def test_relay_follows_discovered_executions_into_the_event_stream():
    provider = FakeProvider()
    provider.handles = [_handle("A"), _handle("B")]
    provider.executions = {"A": [{"execution_id": "e1", "run_id": "run-1", "phase": "running"}], "B": []}
    provider.pages["e1"] = [
        {"cursor": 10, "frames": [_event("a"), _event("b")], "result": None},
        {"cursor": 20, "frames": [_event("c")], "result": {"type": "execution_finished", "run": {}, "session": {}}},
    ]
    relay, stream, state = _relay(provider)
    assert await relay.asweep() == [("A", "e1")]
    await asyncio.wait_for(asyncio.gather(*relay._tasks.values()), 5)
    assert [(index, event.content) for index, event in await stream.replay("run-1")] == [(0, "a"), (1, "b"), (2, "c")]
    assert await stream.get_run_status("run-1") == RunStatus.running, "registered, never completed by the relay"
    assert await state.aget_cursor("A", "e1") == 20
    assert (await state.aget_result("A", "e1"))["type"] == "execution_finished"
    assert await relay.asweep() == [], "finished executions are not followed again"


@pytest.mark.asyncio
async def test_relay_resumes_from_the_committed_cursor_and_retries_after_a_failed_poll():
    provider = FakeProvider()
    provider.handles = [_handle("A")]
    provider.executions = {"A": [{"execution_id": "e1", "run_id": "run-resume", "phase": "running"}]}
    provider.pages["e1"] = [
        {"fail": True},
        {"cursor": 20, "frames": [_event("c", "run-resume")], "result": {"type": "execution_error", "error": "x"}},
    ]
    relay, stream, state = _relay(provider)
    state.cursors[("A", "e1")] = 10  # a previous relay committed up to here
    await relay.asweep()
    await asyncio.wait_for(asyncio.gather(*relay._tasks.values()), 5)
    assert provider.polls[0]["cursor"] == 10, "resumed from the committed cursor, not from zero"
    assert [event.content for _, event in await stream.replay("run-resume")] == ["c"]
    assert await state.aget_cursor("A", "e1") == 20 and (await state.aget_result("A", "e1"))["error"] == "x"


@pytest.mark.asyncio
async def test_relay_skips_serverless_or_paused_sandboxes_and_tolerates_refused_tokens(caplog):
    provider = FakeProvider()
    provider.handles = [_handle("exec-only", url=None), _handle("paused", state="paused"), _handle("bad")]
    provider.executions = {"bad": [{"execution_id": "e9", "run_id": "r", "phase": "running"}]}
    provider.health_error["bad"] = "Sandbox runtime refused the token"
    relay, stream, state = _relay(provider)
    assert await relay.asweep() == []
    assert provider.polls == []
    assert "refused the token" in caplog.text


@pytest.mark.asyncio
async def test_relay_run_stops_on_signal_and_cancels_followers():
    provider = FakeProvider()
    provider.handles = [_handle("A")]
    provider.executions = {"A": [{"execution_id": "e1", "run_id": "run-1", "phase": "running"}]}
    provider.release.clear()  # the runtime never answers
    relay, stream, state = _relay(provider)
    stop = asyncio.Event()
    runner = asyncio.create_task(relay.arun(stop=stop))
    await asyncio.sleep(0.05)
    assert ("A", "e1") in relay._tasks
    stop.set()
    await asyncio.wait_for(runner, 2)
    assert relay._tasks == {}


@pytest.mark.asyncio
async def test_sink_skips_unknown_event_types_and_keeps_the_page_cursor():
    stream, state = InMemoryEventStream(), MemoryRelayState()
    sink = EventStreamRelaySink(state, event_stream=stream)
    page = RelayedPage(
        "s",
        "coder",
        1,
        "e",
        "run-sink",
        10,
        [
            {"event": "NotAnEvent", "run_id": "run-sink"},
            {"event": "ToolCallStarted", "run_id": "run-sink", "agent_id": "coder"},
        ],
        None,
    )
    await sink.apublish(page)
    assert [event.event for _, event in await stream.replay("run-sink")] == ["ToolCallStarted"]
    assert await state.aget_cursor("s", "e") == 10
