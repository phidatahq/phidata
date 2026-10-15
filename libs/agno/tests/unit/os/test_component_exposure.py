"""Deployment exposure must agree across transports, runners and stored references."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.db.base import ComponentType
from agno.db.sqlite import SqliteDb
from agno.exceptions import ComponentRehydrationError
from agno.models.base import Model
from agno.models.message import MessageMetrics
from agno.models.response import ModelResponse
from agno.os import AgentOS, OSManager
from agno.os.config import AgentOSConfig, Manifest
from agno.registry import ComponentPolicy, Registry
from agno.registry._reserved import BUILDER_ID, MANAGER_TEAM_ID, OPERATOR_ID
from agno.team import Team
from agno.tools import tool
from agno.tools.scheduler import SchedulerTools
from agno.tools.studio_runner import StudioRunnerTools
from agno.workflow import Workflow


class FixtureModel(Model):
    def __init__(self, tool_name=None, arguments=None):
        super().__init__(id="exposure-fixture", provider="test")
        self.tool_name = tool_name
        self.arguments = arguments or {}
        self.calls = 0

    def invoke(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1 and self.tool_name:
            return ModelResponse(
                role="assistant",
                tool_calls=[
                    {
                        "id": "fixture-call",
                        "type": "function",
                        "function": {"name": self.tool_name, "arguments": json.dumps(self.arguments)},
                    }
                ],
                response_usage=MessageMetrics(),
            )
        return ModelResponse(content="fixture completed", role="assistant", response_usage=MessageMetrics())

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
    return SqliteDb(db_file=str(tmp_path / "exposure.db"))


def store(db, kind, component_id, name=None, **config):
    db.create_component_with_config(
        component_id=component_id,
        component_type=ComponentType(kind),
        name=name or component_id,
        config={"name": name or component_id, "model": {"id": "exposure-fixture", "provider": "test"}, **config},
        stage="published",
    )


@pytest.mark.parametrize("kind", ["agent", "team", "workflow"])
@pytest.mark.parametrize("use_async", [False, True])
def test_internal_catalog_resolution_refuses_ids_names_versions_and_metadata(db, kind, use_async):
    from importlib import import_module

    from agno.os import utils

    model = FixtureModel()
    registry = Registry(models=[model], component_policies=[ComponentPolicy(kind, "private", public=False)])
    store(db, kind, "private", "Private Display Name", metadata={"public": True, "_agno": {"internal": False}})
    store(db, kind, "ordinary")
    module = import_module(f"agno.{kind}.{kind}")
    loader = getattr(module, f"get_{kind}_by_id")
    for version in (None, 1):
        assert loader(db=db, id="private", version=version, registry=registry, published_only=False) is None
    listing = getattr(module, f"get_{kind}s")(db=db, registry=registry)
    assert [c.id for c in listing] == ["ordinary"]
    resolver = getattr(utils, f"get_{kind}_by_id" + ("_async" if use_async else ""))
    result = resolver(**{f"{kind}_id": "private", "db": db, "registry": registry})
    assert (asyncio.run(result) if use_async else result) is None
    runner = StudioRunnerTools(db=db, registry=registry, include_all_components=True)
    run = getattr(runner, ("arun_" if use_async else "run_") + kind)
    for reference in ("private", "Private Display Name", "private-display-name"):
        result = run(**{f"{kind}_id": reference, "message": "must not run"})
        assert "error" in json.loads(asyncio.run(result) if use_async else result)
    data = json.loads(getattr(runner, f"list_{kind}s")())
    assert data["count"] == data["total"] == 1
    assert [c["id"] for c in data[kind + "s"]] == ["ordinary"]
    assert model.calls == 0
    # Policy does not delete, archive or conceal records from the storage/admin plane.
    assert db.get_component("private")["current_version"] == 1


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("use_async", [False, True])
def test_reserved_rows_cannot_impersonate_runtime_components(db, enabled, use_async):
    model = FixtureModel()
    registry = Registry(models=[model])
    os = AgentOS(
        db=db,
        registry=registry,
        manager=OSManager(model=model, access_docs=False) if enabled else False,
        telemetry=False,
    )
    for cid in (BUILDER_ID, OPERATOR_ID):
        store(db, "agent", cid, "Legacy " + cid)
    store(db, "team", MANAGER_TEAM_ID)
    store(db, "agent", "ordinary")
    runner = (
        os.manager.tools[0] if enabled else StudioRunnerTools(db=db, registry=registry, include_all_components=True)
    )
    for cid in (BUILDER_ID, OPERATOR_ID):
        for reference in (cid, "Legacy " + cid):
            result = asyncio.run(runner.arun_agent(reference, "hi")) if use_async else runner.run_agent(reference, "hi")
            assert "error" in json.loads(result)
    data = json.loads(runner.list_agents())
    assert data["count"] == data["total"] == 1
    assert data["agents"][0]["id"] == "ordinary"
    teams = json.loads(runner.list_teams())
    assert teams["total"] == int(enabled)
    assert model.calls == 0


@pytest.mark.parametrize("resync", [False, True])
def test_application_policy_is_typed_and_filters_public_surfaces(db, resync):
    private = Agent(id="same-id", name="Private Agent", model=FixtureModel())
    public_team = Team(id="same-id", name="Public Team", members=[private], model=FixtureModel())
    private_workflow = Workflow(id="private-flow", steps=[])
    registry = Registry(
        component_policies=[
            ComponentPolicy("agent", private.id, public=False),
            ComponentPolicy("workflow", private_workflow.id, public=False),
        ]
    )
    os = AgentOS(
        agents=[private],
        teams=[public_team],
        workflows=[private_workflow],
        registry=registry,
        db=db,
        config=AgentOSConfig(manifest={"private-flow": Manifest(description="hidden")}),
        telemetry=False,
    )
    app = os.get_app()
    if resync:
        os.resync(app)
    client = TestClient(app)
    config = client.get("/config").json()
    assert config["agents"] == config["workflows"] == []
    assert [t["id"] for t in config["teams"]] == ["same-id"]
    assert "private-flow" not in config["manifest"]
    assert client.get("/agents").json() == client.get("/workflows").json() == []
    assert not client.get("/teams/same-id").json().get("members")
    assert client.get("/agents/same-id").status_code == 404
    assert client.post("/agents/same-id/runs", data={"message": "hi"}).status_code == 404
    assert client.post("/workflows/private-flow/runs", data={"message": "hi"}).status_code == 404
    assert client.post("/teams/same-id/runs", data={"message": "hi", "stream": "false"}).status_code == 200
    # Initialization still sees internal code-defined agents.
    assert private.store_events
    runner = StudioRunnerTools(db=db, registry=registry, include_agents=[private])
    assert "error" in json.loads(runner.run_agent(private.id, "hi"))
    assert json.loads(runner.list_agents())["count"] == 0


@pytest.mark.parametrize("kind", ["agent", "team", "workflow"])
def test_policy_applies_before_factories_run(db, kind):
    from agno.agent import AgentFactory
    from agno.os import utils
    from agno.team import TeamFactory
    from agno.workflow import WorkflowFactory

    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Private factory must not run")

    factory_type = {"agent": AgentFactory, "team": TeamFactory, "workflow": WorkflowFactory}[kind]
    factory = factory_type(id="private", db=db, factory=forbidden)
    registry = Registry(component_policies=[ComponentPolicy(kind, "private", public=False)])
    args = {f"{kind}_id": "private", kind + "s": [factory], "registry": registry, "db": db}
    assert getattr(utils, f"get_{kind}_by_id")(**args) is None
    assert asyncio.run(getattr(utils, f"get_{kind}_by_id_async")(**args)) is None
    assert calls == []


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize("version", [None, 1])
def test_stored_team_and_workflow_cannot_import_noncomposable_components(db, public, version):
    from agno.workflow.step import Step

    registry = Registry(
        models=[FixtureModel()],
        component_policies=[ComponentPolicy("agent", "member", public=public, composable=False)],
    )
    store(db, "agent", "member")
    links = [{"link_kind": "member", "child_component_id": "member", "child_version": version}]
    with pytest.raises(ComponentRehydrationError, match="not available for composition"):
        Team.from_dict(
            {"name": "stored", "members": [{"type": "agent", "agent_id": "member"}]},
            db=db,
            registry=registry,
            links=links,
            strict=True,
        )
    with pytest.raises(ComponentRehydrationError, match="not available for composition"):
        Step.from_dict({"name": "stored-step", "agent_id": "member"}, db=db, registry=registry, strict=True)


@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("suffix", ["", "?source=schedule", "/"])
def test_scheduler_tools_refuse_private_targets_and_old_jobs(db, use_async, suffix):
    registry = Registry(component_policies=[ComponentPolicy("agent", "private", public=False)])
    scheduler = SchedulerTools(db=db, registry=registry)
    path = "/agents/%70rivate/runs" + suffix
    args = dict(name="invalid", cron="0 0 * * *", endpoint=path, payload='{"message":"hi"}')
    result = asyncio.run(scheduler.acreate_schedule(**args)) if use_async else scheduler.create_schedule(**args)
    assert json.loads(result)["error_type"] == "target_internal"
    old = scheduler.manager.create(name="old", cron="0 0 * * *", endpoint=path, payload={"message": "hi"})
    for method in ("enable_schedule", "trigger_schedule"):
        result = getattr(scheduler, ("a" if use_async else "") + method)(old.id)
        assert json.loads(asyncio.run(result) if use_async else result)["error_type"] == "target_internal"
    assert json.loads(scheduler.disable_schedule(old.id))["status"] == "disabled"
    assert json.loads(scheduler.delete_schedule(old.id))["status"] == "deleted"


@pytest.mark.parametrize(
    "target",
    [
        "/agents/private/runs",
        "/agents/%70rivate/runs?source=schedule",
        "/agents/public/../private/runs",
        "/agents/private/runs/old/continue",
    ],
)
def test_http_schedule_conflicts_and_migration(db, target):
    registry = Registry(component_policies=[ComponentPolicy("agent", "private", public=False)])
    os = AgentOS(db=db, registry=registry, telemetry=False)
    client = TestClient(os.get_app())
    data = {"name": "job", "cron_expr": "0 0 * * *", "endpoint": target, "payload": {"message": "hi"}}
    assert client.post("/schedules", json=data).status_code == 409
    old = SchedulerTools(db=db).manager.create(name="old", cron="0 0 * * *", endpoint=target)
    for suffix in ("enable", "trigger"):
        response = client.post(f"/schedules/{old.id}/{suffix}")
        assert response.status_code == 409, response.text
    assert client.patch(f"/schedules/{old.id}", json={"endpoint": "/agents/public/runs"}).status_code == 200
    assert client.delete(f"/schedules/{old.id}").status_code == 204


@pytest.mark.parametrize("stream", [False, True])
def test_internal_member_confirmation_continues_through_owner(db, stream):
    calls = []

    @tool(requires_confirmation=True)
    def approved_action() -> str:
        """Execute the local fixture action."""
        calls.append(True)
        return "action complete"

    member = Agent(id="private", model=FixtureModel("approved_action"), tools=[approved_action], db=db)
    team = Team(
        id="owner",
        members=[member],
        model=FixtureModel("delegate_task_to_member", {"member_id": "private", "task": "Perform the action"}),
        db=db,
    )
    registry = Registry(component_policies=[ComponentPolicy("agent", "private", public=False)])
    os = AgentOS(db=db, agents=[member], teams=[team], registry=registry, telemetry=False)
    client = TestClient(os.get_app())
    response = client.post("/teams/owner/runs", data={"message": "act", "stream": str(stream).lower()})
    assert response.status_code == 200
    if stream:
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        data = next(event for event in events if event.get("event") == "TeamRunPaused")
    else:
        data = response.json()
        assert data["status"] == "PAUSED"
    assert calls == []
    requirements = data["requirements"]
    for req in requirements:
        req["confirmation"] = True
        req["tool_execution"]["confirmed"] = True
    assert client.post(f"/agents/private/runs/{data['run_id']}/continue", data={"stream": "false"}).status_code == 404
    resumed = client.post(
        f"/teams/owner/runs/{data['run_id']}/continue",
        data={"session_id": data["session_id"], "requirements": json.dumps(requirements), "stream": "false"},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "COMPLETED"
    assert calls == [True]
    history = client.get(f"/sessions/{data['session_id']}/runs").json()
    assert any(run.get("agent_id") == "private" for run in history)


@pytest.mark.asyncio
async def test_mcp_obeys_application_policy(db):
    from fastmcp import Client

    from agno.os.mcp import build_mcp_server

    private = Agent(id="private", model=FixtureModel())
    ordinary = Agent(id="ordinary", model=FixtureModel())
    registry = Registry(component_policies=[ComponentPolicy("agent", "private", public=False)])
    os = AgentOS(db=db, agents=[private, ordinary], registry=registry, telemetry=False)
    os.get_app()
    async with Client(build_mcp_server(os)) as client:
        config = await client.call_tool("get_agentos_config", {})
        text = " ".join(b.text for b in config.content if hasattr(b, "text"))
        assert '"private"' not in text and '"ordinary"' in text
        with pytest.raises(Exception, match="not found"):
            await client.call_tool("run_agent", {"agent_id": "private", "message": "hi"})
        result = await client.call_tool("run_agent", {"agent_id": "ordinary", "message": "hi"})
        assert not result.is_error


@pytest.mark.parametrize("kind", ["agent", "team", "workflow"])
@pytest.mark.asyncio
async def test_queue_rechecks_policy_before_replaying_old_jobs(db, kind):
    from types import SimpleNamespace

    from agno.job_queue.config import QueueConfig
    from agno.job_queue.store import InMemoryQueueStore
    from agno.os.job_queue import get_active_queue_worker, queue_lifespan

    agent = Agent(id="private", model=FixtureModel(), db=db)
    team = Team(id="private", members=[agent], model=FixtureModel(), db=db)
    workflow = Workflow(id="private", steps=[agent], db=db)
    registry = Registry(component_policies=[ComponentPolicy(kind, "private", public=False)])
    os = SimpleNamespace(
        db=db,
        registry=registry,
        agents=[agent],
        teams=[team],
        workflows=[workflow],
        queue=QueueConfig(durable=True, db=InMemoryQueueStore()),
    )
    app = SimpleNamespace(state=SimpleNamespace())
    async with queue_lifespan(app, os):
        worker = get_active_queue_worker()
        for source in ("registry", "db", "factory"):
            assert (
                await worker._aresolve_job_component(
                    {
                        "component_type": kind,
                        "component_id": "private",
                        "payload": {"scope": {"source": source, "version": 1}},
                    }
                )
                is None
            )
    assert agent.model.calls == team.model.calls == 0


def test_hosted_tools_cannot_omit_or_replace_deployment_policy(db):
    private = Agent(id="private", model=FixtureModel())
    runner = StudioRunnerTools(include_agents=[private])
    scheduler = SchedulerTools(db=db)
    caller = Agent(id="caller", model=FixtureModel(), tools=[runner, scheduler])
    registry = Registry(component_policies=[ComponentPolicy("agent", "private", public=False)])
    os = AgentOS(db=db, agents=[private, caller], registry=registry, telemetry=False)
    os.get_app()
    assert runner.registry is scheduler.registry is registry
    assert "error" in json.loads(runner.run_agent("private", "hi"))
    assert (
        json.loads(
            scheduler.create_schedule(
                name="no", cron="0 0 * * *", endpoint="/agents/private/runs", payload='{"message":"hi"}'
            )
        )["error_type"]
        == "target_internal"
    )
    runner.registry = Registry()
    with pytest.raises(ValueError, match="share the AgentOS registry"):
        os.resync(os.get_app())


def test_public_noncomposable_component_still_runs(db):
    agent = Agent(id="run-only", model=FixtureModel())
    registry = Registry(component_policies=[ComponentPolicy("agent", agent.id, composable=False)])
    os = AgentOS(db=db, agents=[agent], registry=registry, telemetry=False)
    client = TestClient(os.get_app())
    assert client.post("/agents/run-only/runs", data={"message": "hi", "stream": "false"}).status_code == 200
    assert registry.get_agent(agent.id) is None
    runner = StudioRunnerTools(registry=registry, include_agents=[agent])
    assert json.loads(runner.run_agent(agent.id, "hi"))["content"] == "fixture completed"
    from agno.tools.studio import StudioTools

    studio = StudioTools(registry=registry, db=db, include_agents=[agent])
    result = json.loads(
        studio.create_team(name="wrapper", member_ids=[agent.id], instructions="Delegate", publish=True)
    )
    assert not result["ok"]
    assert db.get_component("wrapper") is None


def test_automatic_a2a_obeys_current_policy_after_resync(db):
    agent = Agent(id="researcher", model=FixtureModel())
    team = Team(id="owner", members=[agent], model=FixtureModel())
    registry = Registry()
    os = AgentOS(db=db, agents=[agent], teams=[team], registry=registry, a2a_interface=True, telemetry=False)
    app = os.get_app()
    client = TestClient(app)
    path = "/a2a/agents/researcher/.well-known/agent-card.json"
    assert client.get(path).status_code == 200
    registry.component_policies = [ComponentPolicy("agent", "researcher", public=False)]
    os.resync(app)
    assert client.get(path).status_code == 404
    assert client.get("/agents").json() == []
    assert registry.get_agent("researcher") is None


@pytest.mark.parametrize("use_async", [False, True])
def test_studio_schedule_message_edits_obey_policy(db, use_async):
    from agno.tools.studio import StudioTools

    registry = Registry(component_policies=[ComponentPolicy("agent", "private", public=False)])
    studio = StudioTools(db=db, registry=registry, schedules=True)
    old = SchedulerTools(db=db).manager.create(
        name="old", cron="0 0 * * *", endpoint="/agents/private/runs", payload={"message": "original"}
    )
    update = studio.aupdate_schedule if use_async else studio.update_schedule
    result = update(old.id, message="replacement")
    data = json.loads(asyncio.run(result) if use_async else result)
    assert not data["ok"]
    assert "internal" in data["error"]["message"]
    assert db.get_schedule(old.id)["payload"]["message"] == "original"
    result = update(old.id, description="Migrate this schedule")
    assert json.loads(asyncio.run(result) if use_async else result)["ok"]
