import asyncio
import warnings
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from agno.agent import Agent
from agno.agents._config import agent_dataclass
from agno.agents.base import BaseExternalAgent
from agno.agents.claude import ClaudeAgent
from agno.agents.codex import CodexAgent
from agno.run.agent import RunContentEvent, RunOutput
from agno.run.base import RunStatus
from agno.run.status_persist import queue_terminal_writer
from agno.sandbox import Sandbox, _harness
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.fixture import FixtureAgent


class FakeSandbox(Sandbox):
    def __init__(self, env=None, network="isolated"):
        self.env = env
        self.network = network

    async def acreate(self, session_id, *, agent_id=None, generation=1, env=None):
        raise NotImplementedError

    async def aget(self, provider_ref):
        raise NotImplementedError

    async def aexec(self, handle, command, **kwargs):
        raise NotImplementedError

    async def astop(self, handle):
        raise NotImplementedError

    async def adestroy(self, handle):
        raise NotImplementedError


class FakeCoordinator:
    def __init__(self):
        self.calls = []
        self.stream_closed = False

    @staticmethod
    def _result(session_id, execution):
        # The runtime returns structured output as a JSON value, never the caller's model.
        structured = execution["config"].get("output_schema") is not None
        return RunOutput(
            run_id=execution["run_id"],
            session_id=session_id,
            agent_id=execution["agent_id"],
            status=RunStatus.completed,
            content={"answer": "done"} if structured else "done",
        )

    async def arun(self, session_id, **execution):
        self.calls.append((session_id, execution))
        return self._result(session_id, execution)

    async def _astream(self, session_id, **execution):
        self.calls.append((session_id, execution))
        try:
            yield RunContentEvent(run_id=execution["run_id"], content="one")
            yield RunContentEvent(run_id=execution["run_id"], content="two")
            yield self._result(session_id, execution)
        finally:
            self.stream_closed = True


@pytest.fixture
def coordinator(monkeypatch):
    fake = FakeCoordinator()
    monkeypatch.setattr(_harness, "coordinator", lambda agent: fake)
    return fake


@pytest.fixture
def sandbox():
    return FakeSandbox()


@pytest.mark.asyncio
async def test_claude_settings_travel_as_json(coordinator, sandbox, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "host-key")
    agent = ClaudeAgent(id="coder", permission_mode="acceptEdits", allowed_tools=["Read"], max_turns=3, sandbox=sandbox)
    result = await agent.arun("hello", session_id="s1")
    assert result.content == "done"
    session_id, execution = coordinator.calls[0]
    assert (session_id, execution["agent_id"], execution["sdk"], execution["input"]) == (
        "s1",
        "coder",
        "claude",
        "hello",
    )
    assert execution["env"] == {"ANTHROPIC_API_KEY": "host-key"}
    config = execution["config"]
    assert config["permission_mode"] == "acceptEdits"
    assert config["allowed_tools"] == ["Read"]
    assert config["max_turns"] == 3
    assert not {"id", "db", "sandbox", "store_events", "cwd", "retries"} & set(config)


@pytest.mark.asyncio
async def test_sandbox_env_overrides_the_host_model_key(coordinator, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "host-key")
    agent = CodexAgent(id="coder", sandbox=FakeSandbox(env={"OPENAI_API_KEY": "scoped", "EXTRA": "1"}))
    await agent.arun("hello", session_id="s1")
    _, execution = coordinator.calls[0]
    assert execution["env"] == {"OPENAI_API_KEY": "scoped", "EXTRA": "1"}


@pytest.mark.asyncio
async def test_codex_sandbox_mode_travels_with_its_new_name(coordinator, sandbox):
    agent = CodexAgent(id="coder", sandbox_mode="workspace-write", sandbox=sandbox)
    await agent.arun("hello", session_id="s1")
    _, execution = coordinator.calls[0]
    assert execution["sdk"] == "codex"
    assert execution["config"]["sandbox_mode"] == "workspace-write"


@pytest.mark.asyncio
async def test_stream_delegates_and_closes_the_coordinator_stream(coordinator, sandbox):
    agent = ClaudeAgent(id="coder", sandbox=sandbox)
    stream = agent.arun("hello", session_id="s1", stream=True)
    async for event in stream:
        assert event.content == "one"
        break
    await stream.aclose()
    assert coordinator.stream_closed


@pytest.mark.parametrize(
    "build, field",
    [
        (lambda sandbox: ClaudeAgent(cwd="/tmp", sandbox=sandbox), "cwd"),
        (lambda sandbox: ClaudeAgent(retries=2, sandbox=sandbox), "retries"),
        (lambda sandbox: CodexAgent(codex_bin="/usr/bin/codex", sandbox=sandbox), "codex_bin"),
        (lambda sandbox: CodexAgent(env={"A": "1"}, sandbox=sandbox), "env"),
    ],
)
def test_host_only_settings_are_rejected(sandbox, build, field):
    with pytest.raises(ValueError, match="Not supported with sandbox=: " + field):
        build(sandbox)


def test_non_json_setting_is_rejected_by_name(sandbox):
    with pytest.raises(ValueError, match="'mcp_servers' must be a JSON value"):
        ClaudeAgent(mcp_servers=Path("servers.json"), sandbox=sandbox)


def test_sandboxed_agent_requires_postgres(sandbox):
    with pytest.raises(ValueError, match="requires a PostgresDb"):
        ClaudeAgent(db=MagicMock(), sandbox=sandbox)


def test_agentos_rejects_a_sandboxed_agent_without_postgres_at_startup(sandbox):
    from agno.os import AgentOS

    with pytest.raises(ValueError, match="requires a PostgresDb"):
        AgentOS(agents=[ClaudeAgent(id="coder", sandbox=sandbox)], telemetry=False)


def test_adapter_without_a_sandbox_runtime_is_rejected(sandbox):
    @agent_dataclass
    class HostOnlyAgent(BaseExternalAgent):
        pass

    with pytest.raises(ValueError, match="HostOnlyAgent cannot run in a sandbox"):
        HostOnlyAgent(sandbox=sandbox)


def test_fixture_harness_requires_runtime_opt_in(sandbox):
    with pytest.raises(ValueError, match="explicit test-runtime opt-in"):
        FixtureAgent(sandbox=sandbox)
    opted_in = FakeSandbox(env={"AGNO_SANDBOX_TEST_RUNTIME": "1"})
    assert FixtureAgent(sandbox=opted_in).sandbox is opted_in


def test_unreachable_model_network_is_warned(monkeypatch):
    warned = []
    monkeypatch.setattr(_harness, "log_warning", warned.append)
    ClaudeAgent(sandbox=DockerSandbox("agno-sandbox:claude"))
    assert warned and "network='isolated'" in warned[0]


def test_docker_sandbox_carries_harness_settings():
    store = MagicMock()
    sandbox = DockerSandbox("agno-sandbox:claude", checkpoints=store, env={"A": "1"}, execution_timeout=60)
    assert (sandbox.checkpoints, sandbox.env, sandbox.execution_timeout) == (store, {"A": "1"}, 60)
    assert type(sandbox.checkpoint_transfer(store)).__name__ == "DockerCheckpointTransfer"
    with pytest.raises(ValueError, match="execution timeout"):
        DockerSandbox("agno-sandbox:claude", execution_timeout=0)


@pytest.mark.asyncio
async def test_unsupported_run_options_are_rejected(coordinator, sandbox):
    agent = ClaudeAgent(id="coder", sandbox=sandbox)
    with pytest.raises(ValueError, match="Unsupported sandbox run options: dependencies"):
        await agent.arun("hello", session_id="s1", dependencies={"a": 1})


def test_codex_string_sandbox_is_a_deprecated_alias_for_sandbox_mode():
    with pytest.warns(DeprecationWarning, match="use sandbox_mode") as record:
        agent = CodexAgent(sandbox="read-only")
    assert record[0].filename == __file__
    assert agent.sandbox_mode == "read-only"
    assert agent.sandbox is None


def test_codex_rejects_both_sandbox_spellings():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with pytest.raises(ValueError, match="not both sandbox and sandbox_mode"):
            CodexAgent(sandbox="read-only", sandbox_mode="read-only")


def test_native_agent_sandbox_is_not_supported_yet(sandbox):
    with pytest.raises(NotImplementedError, match="ClaudeAgent\\(sandbox=...\\)"):
        Agent(sandbox=sandbox)


def test_queue_terminal_writer_exists_only_with_a_sandbox(sandbox):
    assert queue_terminal_writer(ClaudeAgent(id="coder")) is None
    assert queue_terminal_writer(MagicMock()) is None
    assert queue_terminal_writer(ClaudeAgent(id="coder", sandbox=sandbox)) is not None


def test_coordinator_is_built_once_per_sandbox_and_database(tmp_path, monkeypatch):
    from agno.db.postgres import PostgresDb
    from agno.sandbox.checkpoint import FileCheckpointStore

    monkeypatch.setattr(_harness, "_DEFAULT_CHECKPOINTS", tmp_path / "default")
    db = PostgresDb(db_url="postgresql+psycopg://ai:ai@localhost:1/ai")
    shared = DockerSandbox("agno-sandbox:claude", network="isolated", checkpoints=FileCheckpointStore(tmp_path))
    first = ClaudeAgent(id="first", db=db, sandbox=shared)
    second = ClaudeAgent(id="second", db=db, sandbox=shared)
    assert _harness.coordinator(first) is _harness.coordinator(second)
    other_db = ClaudeAgent(
        id="third", db=PostgresDb(db_url="postgresql+psycopg://ai:ai@localhost:1/ai"), sandbox=shared
    )
    assert _harness.coordinator(other_db) is not _harness.coordinator(first)
    unset = ClaudeAgent(id="fourth", db=db, sandbox=DockerSandbox("agno-sandbox:claude", network="isolated"))
    assert _harness.coordinator(unset).transfer.store.root == tmp_path / "default"


class Answer(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_structured_output_is_parsed_into_the_callers_model(coordinator, sandbox):
    agent = ClaudeAgent(id="coder", output_schema=Answer, sandbox=sandbox)
    result = await agent.arun("hello", session_id="s1")
    assert result.content == Answer(answer="done")
    streamed = [event async for event in agent.arun("hello", session_id="s1", stream=True, yield_run_output=True)]
    assert streamed[-1].content == Answer(answer="done")


@pytest.mark.parametrize("value", ["read-only", object()])
def test_sandbox_must_be_a_sandbox(value):
    with pytest.raises(TypeError, match="sandbox= takes a Sandbox"):
        ClaudeAgent(sandbox=value)


@pytest.mark.asyncio
async def test_host_only_setting_assigned_after_construction_is_rejected(coordinator, sandbox):
    agent = CodexAgent(id="coder", sandbox=sandbox)
    agent.codex_bin = "/usr/local/bin/codex"
    with pytest.raises(ValueError, match="Not supported with sandbox=: codex_bin"):
        await agent.arun("hello", session_id="s1")
    assert not coordinator.calls


@pytest.mark.parametrize(
    "build, field",
    [
        (lambda sandbox: CodexAgent(turn_options={"cwd": "/repo"}, sandbox=sandbox), "turn_options"),
        (lambda sandbox: CodexAgent(thread_options={"cwd": "/repo"}, sandbox=sandbox), "thread_options"),
        (lambda sandbox: ClaudeAgent(plugins=[{"type": "local", "path": "/plugins/x"}], sandbox=sandbox), "plugins"),
    ],
)
def test_nested_host_paths_are_rejected(sandbox, build, field):
    with pytest.raises(ValueError, match="Not supported with sandbox=: " + field):
        build(sandbox)


def test_runtime_refuses_a_host_codex_binary():
    from agno.sandbox.protocol import validate_request

    with pytest.raises(ValueError, match="Runtime owns"):
        validate_request(
            dict(
                version=1,
                execution_id="e",
                run_id="r",
                agent_id="a",
                session_id="s",
                sdk="codex",
                input="hello",
                config={"codex_bin": "/usr/local/bin/codex"},
            )
        )


@pytest.mark.asyncio
async def test_cancellation_registration_is_cleaned_up(coordinator, sandbox, monkeypatch):
    import agno.run.cancel as cancel

    cleaned = []
    original = cancel.acleanup_run

    async def record(run_id):
        cleaned.append(run_id)
        await original(run_id)

    monkeypatch.setattr(cancel, "acleanup_run", record)
    agent = ClaudeAgent(id="coder", sandbox=sandbox)
    await agent.arun("hello", session_id="s1", run_id="direct")
    stream = agent.arun("hello", session_id="s1", run_id="streamed", stream=True)
    async for _ in stream:
        break
    await stream.aclose()
    assert cleaned == ["direct", "streamed"]


@pytest.mark.parametrize("operation", ["login_api_key", "alogin_api_key", "compact", "acompact"])
@pytest.mark.asyncio
async def test_codex_host_operations_refuse_a_sandboxed_agent(sandbox, operation):
    agent = CodexAgent(id="coder", sandbox=sandbox)
    method = getattr(agent, operation)
    with pytest.raises(ValueError, match="acts on this host, not the sandbox"):
        result = method("key") if "login" in operation else method("s1")
        if asyncio.iscoroutine(result):
            await result


@pytest.mark.asyncio
async def test_direct_run_carries_the_agent_name(coordinator, sandbox):
    agent = ClaudeAgent(id="coder", name="Coder", sandbox=sandbox)
    await agent.arun("hello", session_id="s1")
    _, execution = coordinator.calls[0]
    assert execution["agent_name"] == "Coder"
