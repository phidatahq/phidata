"""The shell is served as ordinary components and never enters the build palette."""

import asyncio
import json

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
    assert any("run_diagnostics" in getattr(t, "functions", {}) for t in os.shell.operator.tools)
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


@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("by_name", [False, True])
def test_shell_cannot_be_composed_through_explicit_studio_lists(db, workspace, use_async, by_name):
    registry = Registry(models=[OfflineModel()])
    os = AgentOS(db=db, registry=registry, shell=ShellConfig(workspace=workspace), telemetry=False)
    studio = StudioTools(
        registry=registry,
        db=db,
        include_agents=os.agents,
        include_teams=os.teams,
        # Shell exclusion is not the overridable guard for application builders.
        allowed_tools=[c.id for c in os.shell.components],
    )
    assert registry.agents == [] and registry.teams == []
    os.resync(os.get_app())
    assert registry.agents == [] and registry.teams == []
    for component in os.shell.components:
        reference = component.name if by_name else component.id
        kwargs = dict(name="Wrapper", instructions="Delegate", member_ids=[reference], publish=True)
        result = asyncio.run(studio.acreate_team(**kwargs)) if use_async else studio.create_team(**kwargs)
        assert json.loads(result)["error"]["code"] == "tool_not_allowed"
        step = {"name": "Inspect", "type": "step", "team_id" if component is os.shell.team else "agent_id": reference}
        kwargs = dict(name="Flow", steps=[step], publish=True)
        result = asyncio.run(studio.acreate_workflow(**kwargs)) if use_async else studio.create_workflow(**kwargs)
        assert json.loads(result)["error"]["code"] == "tool_not_allowed"
    assert db.get_component("wrapper") is None
    assert db.get_component("flow") is None


def test_resync_repairs_shell_mirrors_and_recursive_collection_stops_at_shell(db, workspace):
    from agno.os.utils import collect_components_from_os
    from agno.team import Team

    registry = Registry(models=[OfflineModel()])
    os = AgentOS(db=db, registry=registry, shell=ShellConfig(workspace=workspace), telemetry=False)
    registry.agents.extend(os.shell.agents)
    registry.teams.append(os.shell.team)
    wrapper = Team(id="wrapper", name="Wrapper", model=OfflineModel(), members=[os.shell.engineer.deep_copy()])
    os.teams.append(wrapper)
    collect_components_from_os(os.agents, os.teams, os.workflows, registry)
    os.resync(os.get_app())
    assert registry.agents == []
    assert [t.id for t in registry.teams] == ["wrapper"]
    assert not registry.tools
    studio = StudioTools(registry=registry, db=db, allowed_tools=["wrapper", ENGINEER_ID])
    result = json.loads(studio.create_team(name="Built", instructions="Delegate", member_ids=["Wrapper"], publish=True))
    assert result["error"]["code"] == "tool_not_allowed"


@pytest.mark.parametrize("declaration", [None, "registry", "os", "agent"])
def test_shell_knowledge_requires_an_independent_build_declaration(db, declaration):
    from agno.agent import get_agent_by_id
    from agno.knowledge import Knowledge
    from agno.learn import LearningMachine

    knowledge = Knowledge(name="lead-only", contents_db=db)
    learning = LearningMachine(name="lead-memory", db=db, model=OfflineModel())
    registry = Registry(models=[OfflineModel()], knowledge=[knowledge] if declaration == "registry" else [])
    app_agent = Agent(id="app", model=OfflineModel(), knowledge=knowledge if declaration == "agent" else None)
    os = AgentOS(
        db=db,
        registry=registry,
        agents=[app_agent],
        knowledge=[knowledge] if declaration == "os" else None,
        shell=ShellConfig(knowledge=knowledge, learning=learning),
        telemetry=False,
    )
    os.resync(os.get_app())
    assert knowledge in os.knowledge_instances  # still served as an ordinary team's resource
    assert (knowledge in registry.knowledge) == (declaration is not None)
    assert learning not in registry.learning
    studio = os.shell.builder.tools[0]
    result = json.loads(
        studio.create_agent(name="Consumer", instructions="Read", knowledge_name=knowledge.name, publish=True)
    )
    if declaration is None:
        assert result["ok"] is False
    else:
        assert result["ok"] is True
        restored = get_agent_by_id(db=db, id=result["data"]["id"], registry=registry, strict=True)
        assert restored.knowledge is knowledge


@pytest.mark.parametrize("provider_kind", ["path", "default", "empty_exclusions", "subclass"])
def test_engineer_normalizes_workspace_and_confines_all_read_tools(db, workspace, tmp_path, provider_kind):
    from agno.context.mode import ContextMode
    from agno.context.workspace import WorkspaceContextProvider

    class CustomProvider(WorkspaceContextProvider):
        def get_tools(self):
            raise AssertionError("The shell must not use replacement platform tools")

    (workspace / "credentials.json").write_text('{"token": "synthetic-credential"}')
    (workspace / "alias.py").symlink_to(workspace / "credentials.json")
    (tmp_path / "outside.txt").write_text("synthetic-credential")
    (workspace / "escape.py").symlink_to(tmp_path / "outside.txt")
    (workspace / "extra.py").write_text("extra source")
    provider = (
        workspace
        if provider_kind == "path"
        else CustomProvider(root=workspace)
        if provider_kind == "subclass"
        else WorkspaceContextProvider(
            root=workspace, exclude_patterns=[] if provider_kind == "empty_exclusions" else None
        )
    )
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel(), workspace=provider), telemetry=False)
    tool = os.shell.engineer.tools[0]
    assert set(tool.functions) == {"read_file", "list_files", "search_content"}
    assert "print" in tool.read_file("main.py")
    for path in (".env", "credentials.json", "alias.py", "./credentials.json", "../outside.txt", "escape.py"):
        assert tool.read_file(path).startswith("Error:")
    assert json.loads(tool.search_content("synthetic-credential"))["matches_found"] == 0
    assert "credentials.json" not in tool.list_files(recursive=True)
    if provider_kind != "path":
        assert provider.mode == ContextMode.default
        if provider_kind == "empty_exclusions":
            assert provider.exclude_patterns == []


@pytest.mark.parametrize("kwargs", [{"allow_paths": [".env"]}, {"exclude_patterns": ["!.env"]}])
def test_engineer_refuses_workspace_exclusion_overrides(db, workspace, kwargs):
    from agno.context.workspace import WorkspaceContextProvider

    with pytest.raises(ValueError, match="cannot override exclusions"):
        AgentOS(
            db=db,
            shell=ShellConfig(model=OfflineModel(), workspace=WorkspaceContextProvider(root=workspace, **kwargs)),
            telemetry=False,
        )


def test_engineer_rejects_an_arbitrary_tool_provider(db):
    with pytest.raises(TypeError, match="WorkspaceContextProvider"):
        AgentOS(db=db, shell=ShellConfig(model=OfflineModel(), workspace=object()), telemetry=False)


class ToolCallingModel(OfflineModel):
    def __init__(self, tool_name, arguments):
        super().__init__()
        self.tool_name = tool_name
        self.arguments = arguments
        self.calls = 0

    def invoke(self, messages, *args, **kwargs):
        self.calls += 1
        assert self.calls <= 6, "Dispatch must terminate"
        if messages[-1].role == "tool":
            return ModelResponse(content=str(messages[-1].content), role="assistant", response_usage=MessageMetrics())
        return ModelResponse(
            role="assistant",
            response_usage=MessageMetrics(),
            tool_calls=[
                {
                    "id": f"call-{self.calls}",
                    "type": "function",
                    "function": {"name": self.tool_name, "arguments": json.dumps(self.arguments)},
                }
            ],
        )

    async def ainvoke(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)


@pytest.mark.parametrize("use_async", [False, True])
def test_operator_executes_diagnostics_in_both_run_modes(db, use_async):
    model = ToolCallingModel("run_diagnostics", {})
    os = AgentOS(db=db, shell=ShellConfig(model=model), telemetry=False)
    result = asyncio.run(os.shell.operator.arun("Diagnose")) if use_async else os.shell.operator.run("Diagnose")
    report = json.loads(result.content)
    assert next(c for c in report["checks"] if c["name"] == "database")["status"] == "PASS"
    assert model.calls == 2


@pytest.mark.parametrize("use_async", [False, True])
def test_shell_self_dispatch_terminates_after_one_nested_run(db, use_async):
    model = ToolCallingModel("run_team", {"team_id": "custom-lead", "message": "Fresh context"})
    os = AgentOS(db=db, shell=ShellConfig(id="custom-lead", model=model), telemetry=False)
    result = (
        asyncio.run(os.shell.team.arun("Consult yourself", user_id="alice"))
        if use_async
        else os.shell.team.run("Consult yourself", user_id="alice")
    )
    assert "already running" in result.content
    assert model.calls == 4
    sessions = db.get_sessions(user_id="alice")
    assert len(sessions) == 2
    assert os.registry.teams == [] and os.registry.agents == []


@pytest.mark.parametrize("use_async", [False, True])
def test_shell_runner_tracks_served_components_after_list_replacement(db, use_async):
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel()), telemetry=False)
    runner = next(t for t in os.shell.team.deep_copy().tools if isinstance(t, StudioRunnerTools))
    app_agent = Agent(id="later", model=OfflineModel(), db=db)
    os.agents = [*os.agents, app_agent]
    kwargs = dict(agent_id="later", message="Hello")
    result = asyncio.run(runner.arun_agent(**kwargs)) if use_async else runner.run_agent(**kwargs)
    assert json.loads(result)["content"] == "local answer"
    kwargs["agent_id"] = OPERATOR_ID
    result = asyncio.run(runner.arun_agent(**kwargs)) if use_async else runner.run_agent(**kwargs)
    assert json.loads(result)["content"] == "local answer"


@pytest.mark.parametrize("component_id", [BUILDER_ID, OPERATOR_ID, ENGINEER_ID, "custom-lead"])
@pytest.mark.parametrize("in_registry", [False, True])
def test_shell_reserves_ids_even_without_an_engineer(db, component_id, in_registry):
    app_agent = Agent(id=component_id, model=OfflineModel())
    with pytest.raises(ValueError, match="reserved for the shell"):
        AgentOS(
            db=db,
            agents=[] if in_registry else [app_agent],
            registry=Registry(agents=[app_agent] if in_registry else []),
            shell=ShellConfig(id="custom-lead", model=OfflineModel()),
            telemetry=False,
        )


def test_resync_rejects_an_application_agent_with_an_unused_reserved_id(db):
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel()), telemetry=False)
    app = os.get_app()
    os.agents.append(Agent(id=ENGINEER_ID, model=OfflineModel()))
    with pytest.raises(ValueError, match="reserved for the shell"):
        os.resync(app)


@pytest.mark.parametrize("copied", [False, True])
def test_shell_exclusion_survives_foreign_registry_mirrors(db, workspace, copied):
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel(), workspace=workspace), telemetry=False)
    agents = [a.deep_copy() for a in os.shell.agents] if copied else os.shell.agents
    team = os.shell.team.deep_copy() if copied else os.shell.team
    foreign = Registry(models=[OfflineModel()], agents=list(agents), teams=[team])
    assert foreign.agents == [] and foreign.teams == []
    studio = StudioTools(
        registry=foreign, db=db, include_agents=agents, include_teams=[team], allowed_tools=[ENGINEER_ID]
    )
    assert foreign.agents == [] and foreign.teams == []
    result = json.loads(
        studio.create_team(name="Wrapper", instructions="Read", member_ids=["Platform Engineer"], publish=True)
    )
    assert result["error"]["code"] == "tool_not_allowed"


@pytest.mark.parametrize("component_id", [BUILDER_ID, OPERATOR_ID, ENGINEER_ID, "custom-lead"])
def test_studio_and_component_api_cannot_mint_reserved_shell_ids(db, component_id):
    registry = Registry(models=[OfflineModel()])
    os = AgentOS(db=db, registry=registry, shell=ShellConfig(id="custom-lead"), telemetry=False)
    studio = os.shell.builder.tools[0]
    result = json.loads(
        studio.create_agent(name="Application agent", component_id=component_id, instructions="Answer", publish=True)
    )
    assert result["error"]["code"] == "component_conflict"
    response = TestClient(os.get_app()).post(
        "/components",
        json={
            "name": "Application agent",
            "component_id": component_id,
            "component_type": "agent",
            "config": {},
        },
    )
    assert response.status_code == 409
    assert db.get_component(component_id) is None


def test_registry_exclusion_does_not_mutate_the_served_lists(db, workspace):
    os = AgentOS(db=db, shell=ShellConfig(model=OfflineModel(), workspace=workspace), telemetry=False)
    app = os.get_app()
    foreign = Registry(agents=os.agents, teams=os.teams)
    assert foreign.agents == [] and foreign.teams == []
    assert len(os.agents) == 3 and os.teams == [os.shell.team]
    os.registry.agents = os.agents
    os.registry.teams = os.teams
    os.resync(app)
    assert os.registry.agents == [] and os.registry.teams == []
    assert len(os.agents) == 3 and os.teams == [os.shell.team]
