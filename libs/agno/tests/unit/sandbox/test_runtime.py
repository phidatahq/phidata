import asyncio
import json
import os
import threading

import pytest

from agno.sandbox import ExecResult, SandboxError, SandboxHandle, runtime
from agno.sandbox.client import RuntimeExecution, SandboxRuntimeClient


@pytest.fixture
def request_data(monkeypatch):
    monkeypatch.setenv("AGNO_SANDBOX_TEST_RUNTIME", "1")
    return {
        "version": 1,
        "execution_id": "e",
        "run_id": "r",
        "session_id": "s",
        "agent_id": "a",
        "sdk": "fixture",
        "input": "hello",
        "config": {},
        "execution_timeout": 2,
    }


@pytest.fixture
def dispatch(tmp_path, monkeypatch, request_data):
    calls = []
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *a, **kw: calls.append((a, kw)))
    monkeypatch.setattr(runtime, "_process_start", lambda pid: "start")
    monkeypatch.setenv("AGNO_SANDBOX_WORKSPACE", str(tmp_path / "workspace"))
    return tmp_path, calls, request_data


def test_duplicate_start_does_not_repeat_execution(dispatch):
    root, calls, request = dispatch
    first = runtime._start(root, request)
    assert runtime._start(root, request) == first
    assert len(calls) == 1
    with pytest.raises(SandboxError, match="different input"):
        runtime._start(root, {**request, "input": "different"})
    with pytest.raises(SandboxError, match="exactly one"):
        runtime._start(root, {**request, "session_id": "other"})
    assert len(calls) == 1


def test_runtime_writer_lock_is_exclusive(tmp_path):
    with runtime._lock(tmp_path / "lock"):
        with pytest.raises(SandboxError, match="already has a writer"):
            with runtime._lock(tmp_path / "lock"):
                pytest.fail("two writers")


def test_execution_journal_replays_without_service_completion(dispatch):
    root, calls, request = dispatch
    runtime._start(root, request)
    runtime._worker(runtime._job(root, "e"))
    first = runtime._poll(root, "e", 0)
    assert first["result"]["type"] == "execution_finished"
    assert first["frames"][0]["event"]["content"] == "hello"
    assert all(frame["event"]["event"] != "RunCompleted" for frame in first["frames"])
    second = runtime._poll(root, "e", first["cursor"])
    assert second["frames"] == [] and second["result"] == first["result"]
    runtime._start(root, request)
    assert len(calls) == 1
    assert (root / "workspace/fixture-effects.txt").read_text() == "r\n"


def test_disappeared_worker_is_unknown_not_automatically_reexecuted(dispatch, monkeypatch):
    root, calls, request = dispatch
    runtime._start(root, request)
    directory = runtime._job(root, "e")
    runtime._atomic(directory / "status.json", runtime._encode({"phase": "running", "pid": 123, "start": "old"}))
    monkeypatch.setattr(runtime, "_process_start", lambda pid: "new")
    result = runtime._poll(root, "e", 0)["result"]
    assert result["type"] == "execution_unknown"
    runtime._start(root, request)
    assert len(calls) == 1


def test_partial_event_is_not_exposed(dispatch):
    root, _, request = dispatch
    runtime._start(root, request)
    directory = runtime._job(root, "e")
    (directory / "events.jsonl").write_bytes(b'{"partial":')
    assert runtime._poll(root, "e", 0)["frames"] == []
    assert runtime._poll(root, "e", 0)["cursor"] == 0


def test_runtime_rejects_invalid_config_and_disabled_fixture(request_data, monkeypatch):
    with pytest.raises(ValueError, match="configuration"):
        runtime._validate({**request_data, "config": {"db": "secret"}})
    with pytest.raises(ValueError, match="timeout"):
        runtime._validate({**request_data, "execution_timeout": float("nan")})
    monkeypatch.delenv("AGNO_SANDBOX_TEST_RUNTIME")
    with pytest.raises(ValueError, match="disabled"):
        runtime._validate(request_data)


def test_runtime_timeout_is_execution_error(dispatch):
    root, _, request = dispatch
    request.update(config={"delay": 1}, execution_timeout=0.01)
    runtime._start(root, request)
    runtime._worker(runtime._job(root, "e"))
    result = runtime._poll(root, "e", 0)["result"]
    assert result["type"] == "execution_error" and result["error"] == "TimeoutError"


def test_frame_and_journal_limits(dispatch, monkeypatch):
    root, _, request = dispatch
    runtime._start(root, request)
    directory = runtime._job(root, "e")
    monkeypatch.setattr(runtime, "_MAX_FRAME", 10)
    with pytest.raises(SandboxError, match="frame limit"):
        runtime._append(directory, {"content": "too large"})
    monkeypatch.setattr(runtime, "_MAX_FRAME", 1000)
    monkeypatch.setattr(runtime, "_MAX_JOURNAL", 10)
    with pytest.raises(SandboxError, match="journal"):
        runtime._append(directory, {"content": "too large"})


HANDLE = SandboxHandle("id", "name", "a", "s", 1, "running", "digest")


class Provider:
    def __init__(self):
        self.requests = []
        self.stopped = False
        self.response = {"version": 1, "execution_id": "e", "accepted": True}
        self.release = None
        self.entered = threading.Event()

    async def arpc(self, computer, operation, payload):
        self.requests.append(json.loads(payload))
        self.entered.set()
        if self.release is not None:
            await self.release.wait()
        return ExecResult(0, json.dumps(self.response), "")

    async def astop(self, computer):
        self.stopped = True


@pytest.mark.asyncio
async def test_client_start_uses_rpc_transport_and_explicit_cancel():
    provider = Provider()
    client = SandboxRuntimeClient(provider)
    execution = await client.astart(HANDLE, execution_id="e", run_id="r", sdk="claude", input="secret prompt")
    assert execution == RuntimeExecution(HANDLE, "e", "r")
    assert provider.requests[0]["input"] == "secret prompt"
    assert provider.requests[0]["session_id"] == "s"
    await client.acancel(execution)
    assert provider.stopped


@pytest.mark.asyncio
async def test_poll_cancellation_drains_rpc_without_cancelling_execution():
    provider = Provider()
    provider.release = asyncio.Event()
    provider.response = {"version": 1, "execution_id": "e", "cursor": 0, "frames": [], "result": None}
    client = SandboxRuntimeClient(provider)
    task = asyncio.create_task(client.apoll(RuntimeExecution(HANDLE, "e", "r")))
    assert await asyncio.to_thread(provider.entered.wait, 2)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    provider.release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not provider.stopped


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        {"version": 2, "execution_id": "e"},
        {"version": 1, "execution_id": "other"},
        {"version": 1, "execution_id": "e", "cursor": -1, "frames": []},
        {"version": 1, "execution_id": "e", "cursor": 1, "frames": [{"type": "event", "event": {"run_id": "other"}}]},
        {
            "version": 1,
            "execution_id": "e",
            "cursor": 1,
            "frames": [{"type": "event", "event": {"event": "RunCompleted"}}],
        },
        {
            "version": 1,
            "execution_id": "e",
            "cursor": 1,
            "frames": [],
            "result": {"type": "execution_finished", "run": {}, "session": {}},
        },
    ],
)
async def test_client_rejects_invalid_identity_and_terminal_frames(response):
    provider = Provider()
    provider.response = response
    with pytest.raises(SandboxError):
        await SandboxRuntimeClient(provider).apoll(RuntimeExecution(HANDLE, "e", "r"))


def test_sync_client_wrappers():
    provider = Provider()
    client = SandboxRuntimeClient(provider)
    execution = client.start(HANDLE, execution_id="e", run_id="r", sdk="claude", input="hello")
    provider.response = {
        "version": 1,
        "execution_id": "e",
        "cursor": 0,
        "frames": [],
        "result": {"type": "execution_error", "error": "fixture"},
    }
    assert client.poll(execution).result["error"] == "fixture"
    assert client.wait_result(execution)["error"] == "fixture"
    assert len(list(client.pages(execution))) == 1
    client.cancel(execution)
    assert provider.stopped


@pytest.mark.asyncio
async def test_sdk_adapter_terminal_event_is_only_an_execution_result(tmp_path, monkeypatch):
    from agno.run.agent import RunCompletedEvent, RunContentEvent, RunOutput
    from agno.run.base import RunStatus
    from agno.session import AgentSession

    disposed = []

    class Engine:
        def dispose(self):
            disposed.append(True)

    class Db:
        db_engine = Engine()

    class Agent:
        db = Db()

        async def arun(self, prompt, **kwargs):
            yield RunContentEvent(run_id="r", session_id="s", agent_id="a", content="hello")
            yield RunCompletedEvent(run_id="r", session_id="s", agent_id="a", content="hello")
            yield RunOutput(run_id="r", session_id="s", agent_id="a", content="hello", status=RunStatus.completed)

        def get_session(self, *args, **kwargs):
            return AgentSession(session_id="s", agent_id="a", session_data={"native_id": "n"})

    monkeypatch.setenv("HOME", os.environ.get("HOME", ""))
    monkeypatch.setenv("CODEX_HOME", "unused")
    monkeypatch.setattr(runtime, "_agent", lambda *args: Agent())
    directory = tmp_path / "jobs/e"
    directory.mkdir(parents=True)
    result = await runtime._execute(directory, {"sdk": "claude", "run_id": "r", "session_id": "s", "input": "hello"})
    assert result["type"] == "execution_finished"
    frames = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    assert len(frames) == 1 and frames[0]["event"]["event"] == "RunContent"
    assert disposed == [True]


def test_completion_racing_poll_cannot_skip_final_events(dispatch, monkeypatch):
    from pathlib import Path

    root, _, request = dispatch
    runtime._start(root, request)
    directory = runtime._job(root, "e")
    path = directory / "events.jsonl"
    path.touch()
    original_open = Path.open
    raced = []

    class RaceStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def __getattr__(self, key):
            return getattr(self.stream, key)

        def read(self, count):
            value = self.stream.read(count)
            if count == 1 and not value and not raced:
                raced.append(True)
                runtime._append(directory, {"event": "RunContent", "content": "last"})
                runtime._atomic(
                    directory / "result.json", runtime._encode({"type": "execution_error", "error": "finished"})
                )
            return value

    def open_with_race(self, *args, **kwargs):
        stream = original_open(self, *args, **kwargs)
        return RaceStream(stream) if self == path and args == ("rb",) else stream

    monkeypatch.setattr(Path, "open", open_with_race)
    first = runtime._poll(root, "e", 0)
    assert first["result"] is None and first["cursor"] == 0
    second = runtime._poll(root, "e", first["cursor"])
    assert second["frames"][0]["event"]["content"] == "last"
    assert second["result"]["error"] == "finished"


# ---------------------------------------------------------------------------
# The runtime as an HTTP server inside the container
# ---------------------------------------------------------------------------


@pytest.fixture
def runtime_server(tmp_path, monkeypatch, request_data):
    """The real server on a loopback port, with the fixture harness and a fake worker start."""
    import threading

    monkeypatch.setattr(runtime, "_process_start", lambda pid: "start")
    calls = []
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *a, **kw: calls.append((a, kw)))
    server = runtime._serve(tmp_path, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", tmp_path, calls, request_data
    finally:
        server.shutdown()
        server.server_close()


def test_server_health_start_and_poll_match_the_stdin_protocol(runtime_server):
    import httpx

    url, root, calls, request_data = runtime_server
    assert httpx.get(url + "/health").json() == {"version": 1, "ok": True}
    accepted = httpx.post(url + "/start", json=request_data)
    assert accepted.status_code == 200 and accepted.json()["accepted"] is True
    # The same request again attaches; a different one is refused with a conflict.
    assert httpx.post(url + "/start", json=request_data).status_code == 200
    assert len(calls) == 1
    conflict = httpx.post(url + "/start", json={**request_data, "input": "other"})
    assert conflict.status_code == 409 and "different input" in conflict.json()["error"]
    page = httpx.post(url + "/poll", json={"execution_id": "e", "cursor": 0}).json()
    assert page == {"version": 1, "execution_id": "e", "cursor": 0, "frames": [], "result": None}
    assert httpx.post(url + "/poll", json={"execution_id": "e", "cursor": -1}).status_code == 400
    assert httpx.post(url + "/nope", json={}).status_code == 404
    assert httpx.get(url + "/poll").status_code == 404


def test_server_long_poll_returns_as_soon_as_the_journal_grows(runtime_server):
    import threading
    import time

    import httpx

    url, root, calls, request_data = runtime_server
    httpx.post(url + "/start", json=request_data)
    directory = runtime._job(root, "e")

    def append_later():
        time.sleep(0.3)
        runtime._append(directory, {"event": "RunContent", "content": "late"})

    threading.Thread(target=append_later, daemon=True).start()
    started = time.monotonic()
    page = httpx.post(url + "/poll", json={"execution_id": "e", "cursor": 0, "wait": 5}, timeout=10).json()
    elapsed = time.monotonic() - started
    assert [frame["event"]["content"] for frame in page["frames"]] == ["late"]
    assert 0.2 < elapsed < 3, "the poll should return when the event lands, not after the full wait"
    # Nothing new: the wait runs out and an empty page comes back.
    started = time.monotonic()
    idle = httpx.post(url + "/poll", json={"execution_id": "e", "cursor": page["cursor"], "wait": 0.3}, timeout=10)
    assert idle.json()["frames"] == [] and time.monotonic() - started >= 0.25


def test_server_requires_its_token_when_one_is_configured(tmp_path, monkeypatch, request_data):
    import threading

    import httpx

    monkeypatch.setattr(runtime, "_process_start", lambda pid: "start")
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *a, **kw: None)
    server = runtime._serve(tmp_path, 0, "secret-token")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert httpx.get(url + "/health").status_code == 401
        assert httpx.post(url + "/start", json=request_data).status_code == 401
        assert httpx.get(url + "/health", headers={"Authorization": "Bearer nope"}).status_code == 401
        good = {"Authorization": "Bearer secret-token"}
        assert httpx.get(url + "/health", headers=good).status_code == 200
        assert httpx.post(url + "/start", json=request_data, headers=good).json()["accepted"] is True
    finally:
        server.shutdown()
        server.server_close()


def test_server_rejects_oversized_and_malformed_requests(runtime_server):
    import httpx

    url, *_ = runtime_server
    assert httpx.post(url + "/start", content=b"[]", headers={"Content-Type": "application/json"}).status_code == 400
    assert httpx.post(url + "/start", content=b"{", headers={"Content-Type": "application/json"}).status_code == 400
    assert httpx.post(url + "/start", content=b"", headers={"Content-Type": "application/json"}).status_code == 413


def test_stdin_poll_honours_wait(dispatch, monkeypatch, capsys):
    import sys
    import time

    root, calls, request_data = dispatch
    runtime._start(root, request_data)
    monkeypatch.setenv("AGNO_SANDBOX_RUNTIME_DIR", str(root))
    from io import BytesIO
    from types import SimpleNamespace

    monkeypatch.setattr(sys, "argv", ["runtime", "poll"])
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=BytesIO(b'{"execution_id":"e","cursor":0,"wait":0.3}')))
    started = time.monotonic()
    runtime.main()
    assert time.monotonic() - started >= 0.25
    assert json.loads(capsys.readouterr().out)["frames"] == []


@pytest.mark.asyncio
async def test_client_long_poll_does_not_sleep_between_pages():
    """With wait, the container holds the request; the client must not add its own delay."""
    provider = Provider()
    client = SandboxRuntimeClient(provider)
    execution = await client.astart(HANDLE, execution_id="e", run_id="r", sdk="claude", input="hello")
    provider.response = {"version": 1, "execution_id": "e", "cursor": 0, "frames": [], "result": None}
    pages = client.apages(execution, timeout=5, poll_interval=5, wait=0.2)
    assert (await pages.__anext__()).events == []
    provider.response = {
        "version": 1,
        "execution_id": "e",
        "cursor": 0,
        "frames": [],
        "result": {"type": "execution_error", "error": "done"},
    }
    assert (await pages.__anext__()).result["error"] == "done"
    assert [request.get("wait") for request in provider.requests[1:]] == [0.2, 0.2]
