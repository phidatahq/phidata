"""The shell is served as ordinary components and never enters the build palette."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from agno.models.base import Model
from agno.models.message import MessageMetrics
from agno.models.response import ModelResponse
from agno.os import AgentOS, ShellConfig
from agno.os.config import AgentOSConfig, Manifest
from agno.os.shell import BUILDER_ID, ENGINEER_ID, OPERATOR_ID, SHELL_TEAM_ID
from agno.registry import Registry
from agno.tools.agentos import AgentOSTools
from agno.tools.studio import StudioTools
from agno.tools.studio_runner import StudioRunnerTools


class OfflineModel(Model):
    def __init__(self):
        super().__init__(id="fixture", provider="test")

    def invoke(self, *args, **kwargs):
        return ModelResponse(content="local answer", role="assistant", response_usage=MessageMetrics())

    async def ainvoke(self, *args, **kwargs):
        return self.invoke()

    def invoke_stream(self, *args, **kwargs):
        yield self.invoke()

    async def ainvoke_stream(self, *args, **kwargs):
        yield self.invoke()

    def parse_args(self, *args, **kwargs):
        return {}

    def _parse_provider_response(self, response, **kwargs):
        return response

    def _parse_provider_response_delta(self, response):
        return response


@pytest.fixture
def db(tmp_path):
    return SqliteDb(db_file=str(tmp_path / "os.db"))


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "README.md").write_text("# Platform\n")
    (root / "main.py").write_text("print('hi')\n")
    (root / ".env").write_text("OPENAI_API_KEY=secret\n")
    return root


def test_shell_true_uses_the_registry_model_and_serves_four_components(db, workspace):
    model = OfflineModel()
    os = AgentOS(db=db, registry=Registry(models=[model]), shell=True, telemetry=False)
    # No workspace: no engineer.
    assert [a.id for a in os.agents] == [BUILDER_ID, OPERATOR_ID]
    assert [t.id for t in os.teams] == [SHELL_TEAM_ID]
    assert os.shell is not None and os.shell.team.name == "Agno"
    assert os.shell.team.model is model and os.shell.builder.model is model
    assert os.shell.engineer is None

    os = AgentOS(db=db, shell=ShellConfig(model=model, workspace=workspace), telemetry=False)
    assert [a.id for a in os.agents] == [BUILDER_ID, OPERATOR_ID, ENGINEER_ID]
    assert os.shell.engineer is not None


def test_shell_needs_a_model_and_a_sync_db(db, tmp_path):
    with pytest.raises(ValueError, match="needs a model"):
        AgentOS(db=db, shell=True, telemetry=False)
    with pytest.raises(ValueError, match="needs AgentOS\\(db="):
        AgentOS(
            agents=[Agent(id="app", model=OfflineModel())], shell=ShellConfig(model=OfflineModel()), telemetry=False
        )
    with pytest.raises(ValueError, match="synchronous"):
        AgentOS(
            db=AsyncSqliteDb(db_file=str(tmp_path / "a.db")), shell=ShellConfig(model=OfflineModel()), telemetry=False
        )


def test_shell_config_validates_name_id_and_history():
    with pytest.raises(ValueError):
        ShellConfig(name=" ")
    with pytest.raises(ValueError):
        ShellConfig(id=BUILDER_ID)
    with pytest.raises(ValueError):
        ShellConfig(num_history_runs=-1)


def test_shell_stays_out_of_the_registry_including_after_resync(db, workspace):
    registry = Registry(models=[OfflineModel()])
    app_agent = Agent(id="app", model=OfflineModel())
    os = AgentOS(db=db, registry=registry, agents=[app_agent], shell=ShellConfig(workspace=workspace), telemetry=False)
    app = os.get_app()
    os.resync(app)
    assert [a.id for a in registry.agents] == ["app"]
    assert registry.teams == []
    # The platform toolkits were not folded into the registry's tool palette either.
    palette = {type(tool).__name__ for tool in registry.tools}
    assert not palette & {"StudioTools", "StudioRunnerTools", "AgentOSTools"}


def test_application_component_cannot_take_a_reserved_id(db):
    with pytest.raises(ValueError, match="Duplicate IDs"):
        AgentOS(
            db=db,
            agents=[Agent(id=BUILDER_ID, model=OfflineModel())],
            shell=ShellConfig(model=OfflineModel()),
            telemetry=False,
        )


def test_builder_operator_and_lead_carry_the_framework_toolkits(db):
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel(), tools=[lambda: "x"]), telemetry=False)
    studio = next(t for t in os.shell.builder.tools if isinstance(t, StudioTools))
    assert studio.registry is os.registry and studio.db is db
    assert set(studio.requires_confirmation_tools) >= {"archive_component", "delete_version", "delete_schedule"}
    assert any(isinstance(t, AgentOSTools) for t in os.shell.operator.tools)
    assert any(getattr(t, "__name__", "") == "run_diagnostics" for t in os.shell.operator.tools)
    runner = next(t for t in os.shell.team.tools if isinstance(t, StudioRunnerTools))
    assert runner.include_all_components and runner.self_dispatch == "once"
    # Attached resources ride the lead.
    assert any(callable(t) and getattr(t, "__name__", "") == "<lambda>" for t in os.shell.team.tools)


def test_engineer_reads_the_workspace_but_not_env_files(db, workspace):
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel(), workspace=workspace), telemetry=False)
    engineer = os.shell.engineer
    assert engineer is not None
    tools = (
        {tool.name: tool for tool in engineer.tools[0].functions.values()}
        if hasattr(engineer.tools[0], "functions")
        else {}
    )
    names = set(tools) or {getattr(t, "__name__", "") for t in engineer.tools}
    assert names & {"list_files", "read_file"}
    read = tools.get("read_file")
    if read is not None:
        assert "print" in read.entrypoint(path="main.py")
        refused = read.entrypoint(path=".env")
        assert "secret" not in refused


def test_manifest_defaults_yield_to_the_application_config(db):
    config = AgentOSConfig(manifest={SHELL_TEAM_ID: Manifest(description="Our lead", quick_prompts=["Hi"])})
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel()), config=config, telemetry=False)
    assert os.config.manifest[SHELL_TEAM_ID].description == "Our lead"
    assert os.config.manifest[BUILDER_ID].quick_prompts
    assert ENGINEER_ID not in os.config.manifest


def test_shell_serves_over_the_ordinary_planes(db):
    os = AgentOS(db=db, shell=ShellConfig(name="Jarvis", model=OfflineModel()), telemetry=False)
    client = TestClient(os.get_app())
    config = client.get("/config").json()
    assert [t["id"] for t in config["teams"]] == [SHELL_TEAM_ID]
    assert {a["id"] for a in config["agents"]} == {BUILDER_ID, OPERATOR_ID}
    assert config["manifest"][SHELL_TEAM_ID]["quick_prompts"]
    run = client.post(f"/teams/{SHELL_TEAM_ID}/runs", data={"message": "hello", "stream": "false"})
    assert run.status_code == 200, run.text
    assert run.json()["content"] == "local answer" and run.json()["team_name"] == "Jarvis"
    sessions = client.get("/sessions?type=team").json()["data"]
    assert [s["session_id"] for s in sessions] == [run.json()["session_id"]]
    member = client.post(f"/agents/{OPERATOR_ID}/runs", data={"message": "status", "stream": "false"})
    assert member.status_code == 200, member.text


def test_diagnostics_report_sync_async_and_required_env(db, monkeypatch):
    monkeypatch.setenv("PRESENT_KEY", "1")
    monkeypatch.delenv("MISSING_KEY", raising=False)
    os = AgentOS(
        db=db, shell=ShellConfig(model=OfflineModel(), required_env=("PRESENT_KEY", "MISSING_KEY")), telemetry=False
    )
    report = os.run_diagnostics()
    by_name = {check.name: check for check in report.checks}
    assert by_name["database"].status == "PASS" and by_name["database"].evidence == "live"
    assert by_name["components"].status == "PASS"
    assert by_name["env:PRESENT_KEY"].status == "PASS" and by_name["env:MISSING_KEY"].status == "FAIL"
    assert report.status == "FAIL"
    assert "secret" not in str(report.to_dict())

    async def inside_loop():
        with pytest.raises(RuntimeError, match="arun_diagnostics"):
            os.run_diagnostics()
        return await os.arun_diagnostics(required_env=())

    clean = asyncio.run(inside_loop())
    assert clean.status == "WARN"  # authorization is off in this fixture
    assert {c.name for c in clean.checks} == {
        "database",
        "authorization",
        "components",
        "registry",
        "interfaces",
        "scheduler",
        "mcp",
    }


def test_diagnostics_without_a_shell(tmp_path):
    os = AgentOS(db=SqliteDb(db_file=str(tmp_path / "bare.db")), telemetry=False)
    assert os.shell is None
    report = os.run_diagnostics()
    assert {c.name for c in report.checks} >= {"database", "scheduler"}


def test_diagnostics_hide_exception_messages(db, monkeypatch):
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel()), telemetry=False)

    def boom(*args, **kwargs):
        raise RuntimeError("password=hunter2")

    monkeypatch.setattr(db, "get_sessions", boom)
    report = os.run_diagnostics(required_env=())
    database = next(c for c in report.checks if c.name == "database")
    assert database.status == "FAIL" and "hunter2" not in database.detail and "RuntimeError" in database.detail
