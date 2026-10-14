"""AgentCore sandbox contracts against a fake data-plane client; no account access."""

import io
import json
import os
import shutil
from types import SimpleNamespace

import pytest

pytest.importorskip("boto3")

from botocore.exceptions import ClientError

from agno.sandbox.agentcore import AgentCoreCheckpointTransfer, AgentCoreSandbox
from agno.sandbox.base import SandboxError
from agno.sandbox.checkpoint import FileCheckpointStore

ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agno_sandbox-abc123"


class Data:
    """Answers like the bedrock-agentcore data plane in front of agentcore_server."""

    def __init__(self):
        self.claims = {}
        self.invokes, self.commands, self.stops, self.staged = [], [], [], {}
        self.conflicts = 0
        self.conflict_code = "RetryableConflictException"
        self.command_reply = {"exitCode": 0, "status": "COMPLETED"}
        self.command_stdout = json.dumps({"exit_code": 0, "stdout": "hi", "stderr": ""})
        self.command_stderr = ""
        self.rpc_reply = {"status": 200, "body": '{"version": 1}'}

    def invoke_agent_runtime(self, **kwargs):
        self.invokes.append(kwargs)
        if self.conflicts:
            self.conflicts -= 1
            raise ClientError({"Error": {"Code": self.conflict_code, "Message": "busy"}}, "Invoke")
        request = json.loads(kwargs["payload"])
        session, operation = kwargs["runtimeSessionId"], request.pop("op")
        reply = {"ok": True}
        if operation == "claim":
            existing = self.claims.get(session)
            if existing and existing != request["metadata"]:
                reply = {"ok": False, "error": "PermissionError: already claimed with a different identity"}
            else:
                self.claims[session] = request["metadata"]
                reply["value"] = {"metadata": request["metadata"], "created": existing is None}
        elif operation == "describe":
            claim = self.claims.get(session)
            reply["value"] = {"claimed": claim is not None, **({"metadata": claim} if claim else {})}
        elif operation == "stage":
            self.staged[request["name"]] = bytes.fromhex(request["data"])
            reply["value"] = {}
        elif operation == "rpc":
            reply["value"] = self.rpc_reply
        return {"response": io.BytesIO(json.dumps(reply).encode())}

    def invoke_agent_runtime_command(self, **kwargs):
        self.commands.append(kwargs)
        delta = {"stdout": self.command_stdout, "stderr": self.command_stderr}
        return {"stream": [{"chunk": {"contentDelta": delta}}, {"chunk": {"contentStop": self.command_reply}}]}

    def stop_runtime_session(self, **kwargs):
        self.stops.append(kwargs["runtimeSessionId"])
        self.claims.pop(kwargs["runtimeSessionId"], None)


def sandbox():
    value = AgentCoreSandbox(ARN, namespace="tests", lifetime=600)
    value._data = Data()
    return value


def test_constructor_validates_arn_and_lifetime():
    for kwargs in ({"runtime_arn": "not-an-arn"}, {"runtime_arn": ARN, "lifetime": 10}):
        with pytest.raises(ValueError):
            AgentCoreSandbox(**kwargs)


@pytest.mark.asyncio
async def test_create_claims_a_deterministic_session_and_is_idempotent():
    value = sandbox()
    first = await value.acreate("s", agent_id="a", env={"MODEL": "x"})
    second = await value.acreate("s", agent_id="a", env={"MODEL": "x"})
    assert first == second and first.provider_ref.startswith("agno-") and len(first.provider_ref) >= 33
    claim = json.loads(value._data.invokes[0]["payload"])
    assert claim["env"] == {"MODEL": "x"} and claim["lifetime"] == 600
    assert claim["metadata"]["config"] == first.config_digest
    other = await value.acreate("s", agent_id="a", generation=2)
    assert other.provider_ref != first.provider_ref


@pytest.mark.asyncio
async def test_create_with_changed_configuration_is_refused():
    value = sandbox()
    await value.acreate("s", env={"MODEL": "x"})
    with pytest.raises(SandboxError, match="different configuration"):
        await value.acreate("s", env={"MODEL": "y"})


@pytest.mark.asyncio
async def test_a_stopped_generation_never_comes_back():
    value = sandbox()
    handle = await value.acreate("s")
    await value.astop(handle)
    assert await value.aget(handle.provider_ref) is None
    with pytest.raises(SandboxError, match="new generation"):
        await value.acreate("s")


@pytest.mark.asyncio
async def test_unclaimed_replacement_compute_is_released_and_reported_gone():
    value = sandbox()
    reference = "agno-" + "f" * 40
    assert await value.aget(reference) is None
    assert value._data.stops == [reference]
    calls = len(value._data.invokes)
    assert await value.aget(reference) is None
    assert len(value._data.invokes) == calls


@pytest.mark.asyncio
async def test_exec_stages_stdin_and_runs_through_the_guard():
    value = sandbox()
    handle = await value.acreate("s")
    result = await value.aexec(handle, ["cat"], stdin=b"input", timeout=5)
    assert result.stdout == "hi"
    command = value._data.commands[0]["body"]["command"]
    assert command.startswith("python -I -m agno.sandbox.agentcore_server exec --stdin ")
    ((name, staged),) = value._data.staged.items()
    assert name in command and json.loads(staged)["argv"] == ["cat"]
    assert value._data.commands[0]["body"]["timeout"] == 20


@pytest.mark.asyncio
async def test_guard_refusal_and_uncertain_commands_stop_compute():
    value = sandbox()
    handle = await value.acreate("s")
    value._data.command_reply = {"exitCode": 125, "status": "COMPLETED"}
    value._data.command_stderr = "AgentCore computer is not claimed; refusing to run on replacement compute\n"
    with pytest.raises(SandboxError, match="unclaimed"):
        await value.aexec(handle, ["true"])
    value = sandbox()
    handle = await value.acreate("s")
    value._data.command_reply = {"exitCode": -1, "status": "TIMED_OUT"}
    with pytest.raises(SandboxError, match="transport failed"):
        await value.aexec(handle, ["sleep", "9"], timeout=1)
    assert value._data.stops == [handle.provider_ref]


@pytest.mark.asyncio
async def test_rpc_forwards_without_touching_compute_on_failure():
    value = sandbox()
    handle = await value.acreate("s")
    assert (await value.arpc(handle, "poll", b'{"wait": 10}')).stdout == '{"version": 1}'
    value._data.rpc_reply = {"status": 500, "body": "boom"}
    failed = await value.arpc(handle, "poll", b"{}")
    assert failed.exit_code == 1 and failed.stderr == "boom"
    assert value._data.stops == []
    with pytest.raises(ValueError):
        await value.arpc(handle, "exec", b"{}")


@pytest.mark.asyncio
async def test_rejections_before_execution_are_retried_and_others_are_not(monkeypatch):
    monkeypatch.setattr("agno.sandbox.agentcore.time.sleep", lambda seconds: None)
    value = sandbox()
    value._data.conflicts = 2
    await value.acreate("s")
    assert len(value._data.invokes) == 3
    value._data.conflict_code = "ThrottlingException"
    value._data.conflicts = 3
    await value.acreate("s")
    assert len(value._data.invokes) == 7
    value._data.conflict_code = "502"
    value._data.conflicts = 1
    await value.acreate("s")
    assert len(value._data.invokes) == 9
    value._data.conflict_code = "ValidationException"
    value._data.conflicts = 1
    with pytest.raises(ClientError):
        await value.acreate("s")


@pytest.mark.asyncio
async def test_commands_never_retry_a_server_error(monkeypatch):
    monkeypatch.setattr("agno.sandbox.agentcore.time.sleep", lambda seconds: None)
    value = sandbox()
    handle = await value.acreate("s")
    calls = []

    def failing(**kwargs):
        calls.append(kwargs)
        raise ClientError({"Error": {"Code": "502", "Message": "bad gateway"}}, "InvokeAgentRuntimeCommand")

    value._data.invoke_agent_runtime_command = failing
    with pytest.raises(ClientError):
        await value.aexec(handle, ["true"])
    assert len(calls) == 1 and value._data.stops == [handle.provider_ref]


@pytest.mark.asyncio
async def test_pause_is_not_supported():
    value = sandbox()
    handle = await value.acreate("s")
    with pytest.raises(NotImplementedError):
        await value.apause(handle)


@pytest.fixture
def computer(tmp_path, monkeypatch):
    """The in-computer server's checkpoint operations, on temporary directories."""
    from agno.sandbox import agentcore_server as server

    workspace, runtime, control = tmp_path / "workspace", tmp_path / "runtime", tmp_path / "control"
    for path in (workspace, runtime, control):
        path.mkdir()
    monkeypatch.setattr(server, "_CONTROL", control)
    monkeypatch.setattr(server, "_ROOTS", {"workspace": workspace, "native": runtime / "native"})
    monkeypatch.setattr(server, "_USER", os.getuid())
    monkeypatch.setattr(server, "_GROUP", os.getgid())
    monkeypatch.setattr(server, "_load_claim", lambda: {"metadata": {}, "env": {}})
    # Freezing this UID's processes would stop the test runner itself.
    monkeypatch.setattr(server, "_freeze", lambda: [])
    value = sandbox()
    fake = value._invoke

    def invoke(reference, operation, **payload):
        if operation not in ("export", "get", "put", "import", "remove"):
            return fake(reference, operation, **payload)
        try:
            return server._OPERATIONS[operation](payload)
        except Exception as error:
            # The real server answers errors in the body, which _invoke raises as SandboxError.
            raise SandboxError(f"AgentCore sandbox refused {operation}: {type(error).__name__}: {error}") from error

    value._invoke = invoke
    return SimpleNamespace(sandbox=value, workspace=workspace, native=runtime / "native", control=control)


@pytest.mark.asyncio
async def test_checkpoint_round_trip_moves_files_in_chunks_and_keeps_exclusions_inside(computer, tmp_path, monkeypatch):
    monkeypatch.setattr("agno.sandbox.agentcore._CHUNK", 1000)
    handle = await computer.sandbox.acreate("s")
    (computer.workspace / "src").mkdir()
    (computer.workspace / "src" / "app.py").write_text("print('hi')\n" * 400)
    (computer.workspace / "link").symlink_to("src/app.py")
    computer.native.mkdir(mode=0o700)
    (computer.native / "transcript.jsonl").write_text('{"turn": 1}\n')
    (computer.native / "codex" / ".tmp").mkdir(parents=True)
    (computer.native / "codex" / ".tmp" / "plugins.bin").write_bytes(b"x" * 5000)
    (computer.native / "codex" / "auth.json").write_text("secret")

    transfer = AgentCoreCheckpointTransfer(computer.sandbox, FileCheckpointStore(tmp_path / "store"))
    reference = await transfer.acapture(handle, state={"turn": 1})
    assert list(computer.control.iterdir()) == []

    for path in (computer.workspace, computer.native):
        shutil.rmtree(path)
    computer.workspace.mkdir()
    replacement = await computer.sandbox.acreate("s", generation=2)
    assert await transfer.arestore(replacement, reference) == {"turn": 1}
    assert (computer.workspace / "src" / "app.py").read_text() == "print('hi')\n" * 400
    assert os.readlink(computer.workspace / "link") == "src/app.py"
    assert (computer.native / "transcript.jsonl").read_text() == '{"turn": 1}\n'
    assert not (computer.native / "codex" / "auth.json").exists()
    assert not (computer.native / "codex" / ".tmp").exists()
    assert list(computer.control.iterdir()) == []


@pytest.mark.asyncio
async def test_restore_into_a_used_computer_stops_it(computer, tmp_path):
    handle = await computer.sandbox.acreate("s")
    transfer = AgentCoreCheckpointTransfer(computer.sandbox, FileCheckpointStore(tmp_path / "store"))
    reference = await transfer.acapture(handle, state={})
    (computer.workspace / "left-over").write_text("x")
    with pytest.raises(SandboxError, match="empty, unused"):
        await transfer.arestore(handle, reference)
    assert computer.sandbox._data.stops == [handle.provider_ref]
