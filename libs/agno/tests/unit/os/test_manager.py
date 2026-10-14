"""The manager is served as ordinary components and never enters the build palette."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from agno.models.base import Model
from agno.models.message import MessageMetrics
from agno.models.response import ModelResponse
from agno.os import AgentOS, ManagerConfig
from agno.os.config import AgentOSConfig, Manifest
from agno.os.platform import BUILDER_ID, ENGINEER_ID, MANAGER_TEAM_ID, MANAGER_TEAM_NAME, OPERATOR_ID
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


def manager_member(os, component_id):
    return next((member for member in os.manager.members if member.id == component_id), None)


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


def test_manager_true_uses_the_registry_model_and_serves_four_components(db, workspace):
    model = OfflineModel()
    os = AgentOS(db=db, registry=Registry(models=[model]), manager=True, telemetry=False)
    # No workspace: no engineer.
    assert [a.id for a in os.agents] == [BUILDER_ID, OPERATOR_ID]
    assert [t.id for t in os.teams] == [MANAGER_TEAM_ID]
    assert os.manager is not None and os.manager.name == MANAGER_TEAM_NAME == "OS Manager"
    assert os.manager.id == MANAGER_TEAM_ID == "os-manager"
    assert os.manager.model is model and manager_member(os, BUILDER_ID).model is model
    assert manager_member(os, ENGINEER_ID) is None

    os = AgentOS(db=db, manager=ManagerConfig(model=model, workspace=workspace), telemetry=False)
    assert [a.id for a in os.agents] == [BUILDER_ID, OPERATOR_ID, ENGINEER_ID]
    assert manager_member(os, ENGINEER_ID) is not None


def test_manager_needs_a_model_and_a_sync_db(db, tmp_path):
    with pytest.raises(ValueError, match="needs a model"):
        AgentOS(db=db, manager=True, telemetry=False)
    with pytest.raises(ValueError, match="needs AgentOS\\(db="):
        AgentOS(
            agents=[Agent(id="app", model=OfflineModel())], manager=ManagerConfig(model=OfflineModel()), telemetry=False
        )
    with pytest.raises(ValueError, match="synchronous"):
        AgentOS(
            db=AsyncSqliteDb(db_file=str(tmp_path / "a.db")),
            manager=ManagerConfig(model=OfflineModel()),
            telemetry=False,
        )


def test_manager_config_validates_name_id_and_history():
    with pytest.raises(ValueError):
        ManagerConfig(name=" ")
    with pytest.raises(ValueError):
        ManagerConfig(id=BUILDER_ID)
    with pytest.raises(ValueError):
        ManagerConfig(num_history_runs=-1)


def test_manager_stays_out_of_the_registry_including_after_resync(db, workspace):
    registry = Registry(models=[OfflineModel()])
    app_agent = Agent(id="app", model=OfflineModel())
    os = AgentOS(
        db=db, registry=registry, agents=[app_agent], manager=ManagerConfig(workspace=workspace), telemetry=False
    )
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
            manager=ManagerConfig(model=OfflineModel()),
            telemetry=False,
        )


def test_builder_operator_and_lead_carry_the_framework_toolkits(db):
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel(), tools=[lambda: "x"]), telemetry=False)
    studio = next(t for t in manager_member(os, BUILDER_ID).tools if isinstance(t, StudioTools))
    assert studio.registry is os.registry and studio.db is db
    assert set(studio.requires_confirmation_tools) >= {"archive_component", "delete_version", "delete_schedule"}
    assert any(isinstance(t, AgentOSTools) for t in manager_member(os, OPERATOR_ID).tools)
    assert any("run_diagnostics" in getattr(t, "functions", {}) for t in manager_member(os, OPERATOR_ID).tools)
    runner = next(t for t in os.manager.tools if isinstance(t, StudioRunnerTools))
    assert runner.include_all_components and runner.self_dispatch == "once"
    # Attached resources ride the lead.
    assert any(callable(t) and getattr(t, "__name__", "") == "<lambda>" for t in os.manager.tools)


def test_engineer_reads_the_workspace_but_not_env_files(db, workspace):
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel(), workspace=workspace), telemetry=False)
    engineer = manager_member(os, ENGINEER_ID)
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
    config = AgentOSConfig(manifest={MANAGER_TEAM_ID: Manifest(description="Our lead", quick_prompts=["Hi"])})
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel()), config=config, telemetry=False)
    assert os.config.manifest[MANAGER_TEAM_ID].description == "Our lead"
    assert os.config.manifest[BUILDER_ID].quick_prompts
    assert ENGINEER_ID not in os.config.manifest


def test_manager_serves_over_the_ordinary_planes(db):
    os = AgentOS(db=db, manager=ManagerConfig(name="Jarvis", model=OfflineModel()), telemetry=False)
    client = TestClient(os.get_app())
    config = client.get("/config").json()
    assert [t["id"] for t in config["teams"]] == [MANAGER_TEAM_ID]
    assert {a["id"] for a in config["agents"]} == {BUILDER_ID, OPERATOR_ID}
    assert config["manifest"][MANAGER_TEAM_ID]["quick_prompts"]
    run = client.post(f"/teams/{MANAGER_TEAM_ID}/runs", data={"message": "hello", "stream": "false"})
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
        db=db, manager=ManagerConfig(model=OfflineModel(), required_env=("PRESENT_KEY", "MISSING_KEY")), telemetry=False
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


def test_diagnostics_without_a_manager(tmp_path):
    os = AgentOS(db=SqliteDb(db_file=str(tmp_path / "bare.db")), telemetry=False)
    assert os.manager is None
    report = os.run_diagnostics()
    assert {c.name for c in report.checks} >= {"database", "scheduler"}


def test_diagnostics_hide_exception_messages(db, monkeypatch):
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel()), telemetry=False)

    def boom(*args, **kwargs):
        raise RuntimeError("password=hunter2")

    monkeypatch.setattr(db, "get_sessions", boom)
    report = os.run_diagnostics(required_env=())
    database = next(c for c in report.checks if c.name == "database")
    assert database.status == "FAIL" and "hunter2" not in database.detail and "RuntimeError" in database.detail


@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("by_name", [False, True])
def test_manager_cannot_be_composed_through_explicit_studio_lists(db, workspace, use_async, by_name):
    registry = Registry(models=[OfflineModel()])
    os = AgentOS(db=db, registry=registry, manager=ManagerConfig(workspace=workspace), telemetry=False)
    studio = StudioTools(
        registry=registry,
        db=db,
        include_agents=os.agents,
        include_teams=os.teams,
        # Manager exclusion is not the overridable guard for application builders.
        allowed_tools=[c.id for c in [os.manager, *os.manager.members]],
    )
    assert registry.agents == [] and registry.teams == []
    os.resync(os.get_app())
    assert registry.agents == [] and registry.teams == []
    for component in [os.manager, *os.manager.members]:
        reference = component.name if by_name else component.id
        kwargs = dict(name="Wrapper", instructions="Delegate", member_ids=[reference], publish=True)
        result = asyncio.run(studio.acreate_team(**kwargs)) if use_async else studio.create_team(**kwargs)
        assert json.loads(result)["error"]["code"] == "tool_not_allowed"
        step = {"name": "Inspect", "type": "step", "team_id" if component is os.manager else "agent_id": reference}
        kwargs = dict(name="Flow", steps=[step], publish=True)
        result = asyncio.run(studio.acreate_workflow(**kwargs)) if use_async else studio.create_workflow(**kwargs)
        assert json.loads(result)["error"]["code"] == "tool_not_allowed"
    assert db.get_component("wrapper") is None
    assert db.get_component("flow") is None


def test_resync_repairs_manager_mirrors_and_recursive_collection_stops_at_manager(db, workspace):
    from agno.os.utils import collect_components_from_os
    from agno.team import Team

    registry = Registry(models=[OfflineModel()])
    os = AgentOS(db=db, registry=registry, manager=ManagerConfig(workspace=workspace), telemetry=False)
    registry.agents.extend(os.manager.members)
    registry.teams.append(os.manager)
    wrapper = Team(
        id="wrapper", name="Wrapper", model=OfflineModel(), members=[manager_member(os, ENGINEER_ID).deep_copy()]
    )
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
def test_manager_knowledge_requires_an_independent_build_declaration(db, declaration):
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
        manager=ManagerConfig(knowledge=knowledge, learning=learning),
        telemetry=False,
    )
    os.resync(os.get_app())
    assert knowledge in os.knowledge_instances  # still served as an ordinary team's resource
    assert (knowledge in registry.knowledge) == (declaration is not None)
    assert learning not in registry.learning
    studio = manager_member(os, BUILDER_ID).tools[0]
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
            raise AssertionError("The manager must not use replacement platform tools")

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
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel(), workspace=provider), telemetry=False)
    tool = manager_member(os, ENGINEER_ID).tools[0]
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
            manager=ManagerConfig(model=OfflineModel(), workspace=WorkspaceContextProvider(root=workspace, **kwargs)),
            telemetry=False,
        )


def test_engineer_rejects_an_arbitrary_tool_provider(db):
    with pytest.raises(TypeError, match="WorkspaceContextProvider"):
        AgentOS(db=db, manager=ManagerConfig(model=OfflineModel(), workspace=object()), telemetry=False)


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
    os = AgentOS(db=db, manager=ManagerConfig(model=model), telemetry=False)
    result = (
        asyncio.run(manager_member(os, OPERATOR_ID).arun("Diagnose"))
        if use_async
        else manager_member(os, OPERATOR_ID).run("Diagnose")
    )
    report = json.loads(result.content)
    assert next(c for c in report["checks"] if c["name"] == "database")["status"] == "PASS"
    assert model.calls == 2


@pytest.mark.parametrize("use_async", [False, True])
def test_manager_self_dispatch_terminates_after_one_nested_run(db, use_async):
    model = ToolCallingModel("run_team", {"team_id": "custom-lead", "message": "Fresh context"})
    os = AgentOS(db=db, manager=ManagerConfig(id="custom-lead", model=model), telemetry=False)
    result = (
        asyncio.run(os.manager.arun("Consult yourself", user_id="alice"))
        if use_async
        else os.manager.run("Consult yourself", user_id="alice")
    )
    assert "already running" in result.content
    assert model.calls == 4
    sessions = db.get_sessions(user_id="alice")
    assert len(sessions) == 2
    assert os.registry.teams == [] and os.registry.agents == []


@pytest.mark.parametrize("use_async", [False, True])
def test_manager_runner_tracks_served_components_after_list_replacement(db, use_async):
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel()), telemetry=False)
    runner = next(t for t in os.manager.deep_copy().tools if isinstance(t, StudioRunnerTools))
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
def test_manager_reserves_ids_even_without_an_engineer(db, component_id, in_registry):
    app_agent = Agent(id=component_id, model=OfflineModel())
    with pytest.raises(ValueError, match="reserved for the manager"):
        AgentOS(
            db=db,
            agents=[] if in_registry else [app_agent],
            registry=Registry(agents=[app_agent] if in_registry else []),
            manager=ManagerConfig(id="custom-lead", model=OfflineModel()),
            telemetry=False,
        )


def test_resync_rejects_an_application_agent_with_an_unused_reserved_id(db):
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel()), telemetry=False)
    app = os.get_app()
    os.agents.append(Agent(id=ENGINEER_ID, model=OfflineModel()))
    with pytest.raises(ValueError, match="reserved for the manager"):
        os.resync(app)


@pytest.mark.parametrize("copied", [False, True])
def test_manager_exclusion_survives_foreign_registry_mirrors(db, workspace, copied):
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel(), workspace=workspace), telemetry=False)
    agents = [a.deep_copy() for a in os.manager.members] if copied else os.manager.members
    team = os.manager.deep_copy() if copied else os.manager
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
def test_studio_and_component_api_cannot_mint_reserved_manager_ids(db, component_id):
    registry = Registry(models=[OfflineModel()])
    os = AgentOS(db=db, registry=registry, manager=ManagerConfig(id="custom-lead"), telemetry=False)
    studio = manager_member(os, BUILDER_ID).tools[0]
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
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel(), workspace=workspace), telemetry=False)
    app = os.get_app()
    foreign = Registry(agents=os.agents, teams=os.teams)
    assert foreign.agents == [] and foreign.teams == []
    assert len(os.agents) == 3 and os.teams == [os.manager]
    os.registry.agents = os.agents
    os.registry.teams = os.teams
    os.resync(app)
    assert os.registry.agents == [] and os.registry.teams == []
    assert len(os.agents) == 3 and os.teams == [os.manager]


@pytest.mark.parametrize("enabled", [None, False])
def test_disabled_manager_needs_neither_a_model_nor_a_workspace(db, enabled):
    os = AgentOS(db=db, manager=enabled, telemetry=False)
    assert os.manager is None
    assert not os.agents and not os.teams
    assert not os.registry._excluded_component_ids


@pytest.mark.parametrize("invalid", ["true", {}, 1, 0])
def test_manager_rejects_values_outside_the_configuration_contract(db, invalid):
    with pytest.raises(TypeError, match="AgentOS.manager must be"):
        AgentOS(db=db, manager=invalid, telemetry=False)


@pytest.mark.parametrize("use_async", [False, True])
def test_manager_property_is_the_served_team_and_runs_directly(db, use_async):
    from agno.team import Team

    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel()), telemetry=False)
    assert type(os.manager) is Team
    assert os.manager is os.teams[0]
    result = (
        asyncio.run(os.manager.arun("Hello", user_id="alice"))
        if use_async
        else os.manager.run("Hello", user_id="alice")
    )
    assert result.content == "local answer"
    assert [s.session_id for s in db.get_sessions(user_id="alice")] == [result.session_id]
    app = os.get_app()
    manager = os.manager
    os.resync(app)
    assert os.manager is manager and os.manager is os.teams[0]
    assert not any(path.startswith("/manager") for path in app.openapi()["paths"])


def test_manager_configuration_does_not_accept_replacement_members():
    with pytest.raises(TypeError, match="members"):
        ManagerConfig(members=[])


def test_scheduler_check_fails_on_an_unreadable_schedules_table(tmp_path):
    import sqlite3

    db_file = tmp_path / "broken.db"
    os = AgentOS(db=SqliteDb(db_file=str(db_file)), scheduler=True, telemetry=False)
    os.get_app()
    # A schedules table of the wrong shape: every real query against it fails, and the
    # adapter's default answer to that is an empty list.
    with sqlite3.connect(db_file) as conn:
        conn.execute("DROP TABLE IF EXISTS agno_schedules")
        conn.execute("CREATE TABLE agno_schedules (id TEXT PRIMARY KEY)")
    assert os.db.get_schedules(enabled=True) == ([], 0)
    scheduler = next(c for c in os.run_diagnostics(required_env=()).checks if c.name == "scheduler")
    assert scheduler.status == "FAIL" and "Error" in scheduler.detail


def test_database_check_reads_one_session_without_runs(db, monkeypatch):
    os = AgentOS(db=db, manager=ManagerConfig(model=OfflineModel()), telemetry=False)
    seen = {}
    original = db.get_sessions

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(db, "get_sessions", spy)
    database = next(c for c in os.run_diagnostics(required_env=()).checks if c.name == "database")
    assert database.status == "PASS"
    assert seen["limit"] == 1 and seen["include_runs"] is False and seen["deserialize"] is False


def test_diagnostics_pass_only_arguments_an_adapter_declares(db, monkeypatch):
    os = AgentOS(db=db, scheduler=True, telemetry=False)

    def narrow_get_sessions(limit=None, page=None, deserialize=True):
        return [], 0

    def narrow_get_schedules(enabled=None, limit=None, page=None):
        return [], 0

    monkeypatch.setattr(db, "get_sessions", narrow_get_sessions)
    monkeypatch.setattr(db, "get_schedules", narrow_get_schedules)
    checks = {c.name: c for c in os.run_diagnostics(required_env=()).checks}
    assert checks["database"].status == "PASS" and checks["scheduler"].status == "PASS"


@pytest.mark.parametrize(
    "status_code,expected",
    [(200, "PASS"), (401, "PASS"), (403, "PASS"), (404, "FAIL"), (503, "FAIL"), (500, "FAIL"), (307, "WARN")],
)
def test_mcp_probe_distinguishes_reachable_from_healthy(db, monkeypatch, status_code, expected):
    import httpx

    os = AgentOS(db=db, mcp=True, telemetry=False)

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, **kwargs):
            assert url == "https://os.example.test/mcp"
            return httpx.Response(status_code)

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    report = os.run_diagnostics(required_env=(), network_probe=True, public_url="https://os.example.test/")
    mcp = next(c for c in report.checks if c.name == "mcp")
    assert mcp.status == expected and mcp.evidence == "live" and str(status_code) in mcp.detail


def test_registry_exclusion_surface_is_public_and_read_only():
    registry = Registry()
    registry.reserve_component_ids(["reserved-id", ""])
    assert registry.excluded_component_ids == frozenset({"reserved-id"})
    with pytest.raises(AttributeError):
        registry.excluded_component_ids.add("other")  # type: ignore[attr-defined]
    agent = Agent(id="served", model=OfflineModel())
    registry.agents.append(agent)
    registry.exclude_components([agent])
    assert registry.agents == []
    assert registry.is_component_excluded(agent) and registry.is_component_excluded(agent.deep_copy())
    assert registry.is_component_excluded(Agent(id="reserved-id", model=OfflineModel()))
    assert not registry.is_component_excluded(Agent(id="free", model=OfflineModel()))


def test_an_existing_platform_team_keeps_its_id_and_name(db):
    os = AgentOS(db=db, manager=ManagerConfig(id="agno", name="Agno", model=OfflineModel()), telemetry=False)
    assert os.manager.id == "agno" and os.manager.name == "Agno"
    assert "agno" in os.registry.excluded_component_ids and MANAGER_TEAM_ID not in os.registry.excluded_component_ids
    run = TestClient(os.get_app()).post("/teams/agno/runs", data={"message": "hello", "stream": "false"})
    assert run.status_code == 200 and run.json()["team_name"] == "Agno"
