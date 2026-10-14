"""Durable queue for factory-backed components.

A factory builds its component per request from a RequestContext. Before
this, every factory submission with ``background=true`` bypassed the durable
queue and executed as a detached task on the accepting replica. Now the
accepting endpoint stamps the request context (user, session, validated
input, trusted claims) on the ticket and the worker invokes the factory
again at claim time with that context, ``request=None``.

Also covers the read routes that resolved a factory without the request and
answered 400 for every poll of a factory run.
"""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from agno.agent import Agent
from agno.agent.factory import AgentFactory
from agno.db.sqlite import SqliteDb
from agno.factory import FactoryValidationError
from agno.job_queue.config import QueueConfig
from agno.job_queue.store import InMemoryQueueStore
from agno.models.base import Model
from agno.models.message import MessageMetrics
from agno.models.response import ModelResponse
from agno.os import AgentOS
from agno.os.job_queue import (
    aresolve_factory_from_scope,
    factory_queue_scope,
    get_active_queue_worker,
    queue_lifespan,
    queue_scope,
    resolve_queue_scope,
)
from agno.team import Team
from agno.team.factory import TeamFactory

BYPASS = "bypasses the durable queue"


class Persona(BaseModel):
    persona: str = "default"


@pytest.fixture()
def db(tmp_path):
    return SqliteDb(db_file=str(tmp_path / "factories.db"))


@pytest.fixture()
def seen():
    """Every RequestContext a factory in these tests was invoked with."""
    return []


@pytest.fixture()
def agent_factory(db, seen):
    def build(ctx):
        seen.append(ctx)
        persona = ctx.input.persona if isinstance(ctx.input, Persona) else "none"
        return Agent(id="fx-agent", name="FX", db=db, instructions=f"persona={persona}")

    return AgentFactory(id="fx-agent", db=db, factory=build, input_schema=Persona)


@pytest.fixture()
def team_factory(db, seen):
    def build(ctx):
        seen.append(ctx)
        return Team(id="fx-team", name="FX Team", db=db, members=[Agent(id="fx-member", name="Member")])

    return TeamFactory(id="fx-team", db=db, factory=build)


class _TrustedStateMiddleware(BaseHTTPMiddleware):
    """Stand-in for the JWT middleware: puts claims and scopes on request.state."""

    async def dispatch(self, request, call_next):
        request.state.claims = {"sub": "alice", "org": "acme"}
        request.state.scopes = ["runs:write", "agents:read"]
        return await call_next(request)


@pytest.fixture()
def harness(db, agent_factory, team_factory, monkeypatch):
    """A real AgentOS whose only components are factories. The worker never
    runs; the prepare seam is a no-op so a 202 means the ticket was enqueued."""

    async def ok_prepare(component, component_type, run_id, session_id, user_id, input):
        return None

    monkeypatch.setattr("agno.os.job_queue.aprepare_queued_run", ok_prepare)
    app = AgentOS(agents=[agent_factory], teams=[team_factory], db=db, telemetry=False).get_app()
    app.add_middleware(_TrustedStateMiddleware)
    store = InMemoryQueueStore()
    app.state.queue_worker = SimpleNamespace(store=store, config=QueueConfig(durable=True))
    client = TestClient(app, raise_server_exceptions=False)
    return SimpleNamespace(app=app, store=store, client=client, db=db)


def _only_job(store):
    assert len(store._jobs) == 1, "exactly one ticket must have been enqueued"
    return next(iter(store._jobs.values()))


class TestFactorySubmissionsRideTheQueue:
    def test_background_submission_stamps_the_request_context(self, harness, caplog):
        resp = harness.client.post(
            "/agents/fx-agent/runs",
            data={
                "message": "hi",
                "stream": "false",
                "background": "true",
                "user_id": "alice",
                "session_id": "s-1",
                "factory_input": json.dumps({"persona": "pirate"}),
            },
        )
        assert resp.status_code == 202, resp.text
        job = _only_job(harness.store)
        assert job["component_type"] == "agent"
        assert job["component_id"] == "fx-agent"
        scope = job["payload"]["scope"]
        assert scope["source"] == "factory"
        assert scope["pinned"] is None
        # Exactly what the door handed the factory, minus the raw request
        assert scope["context"] == {
            "user_id": "alice",
            "session_id": "s-1",
            "input": {"persona": "pirate"},
            "claims": {"sub": "alice", "org": "acme"},
            "scopes": ["agents:read", "runs:write"],
        }
        assert BYPASS not in caplog.text

    def test_team_factory_submission_rides_the_queue(self, harness):
        resp = harness.client.post(
            "/teams/fx-team/runs",
            data={"message": "hi", "stream": "false", "background": "true", "session_id": "t-1"},
        )
        assert resp.status_code == 202, resp.text
        job = _only_job(harness.store)
        assert job["component_type"] == "team"
        assert job["payload"]["scope"]["source"] == "factory"
        assert job["payload"]["scope"]["context"]["session_id"] == "t-1"

    def test_invalid_factory_input_is_refused_at_the_door(self, harness):
        resp = harness.client.post(
            "/agents/fx-agent/runs",
            data={"message": "hi", "stream": "false", "background": "true", "factory_input": '{"persona": 5}'},
        )
        assert resp.status_code == 400, resp.text
        assert len(harness.store._jobs) == 0

    def test_scope_shape(self):
        state = SimpleNamespace(claims={"sub": "bob"}, scopes={"b", "a"})
        scope = factory_queue_scope(state, "bob", "s", '{"k": 1}', pinned=None)
        assert scope == {
            "user_id": "bob",
            "version": None,
            "pinned": None,
            "source": "factory",
            "context": {
                "user_id": "bob",
                "session_id": "s",
                "input": {"k": 1},
                "claims": {"sub": "bob"},
                "scopes": ["a", "b"],
            },
        }
        # The WebSocket door hands the parsed object, not a string
        assert factory_queue_scope(SimpleNamespace(), None, None, {"k": 2})["context"]["input"] == {"k": 2}
        # Nothing the door did not parse rides the ticket
        assert factory_queue_scope(SimpleNamespace(), None, None, "not json")["context"]["input"] is None
        assert factory_queue_scope(SimpleNamespace(), None, None, "[1, 2]")["context"]["input"] is None

    def test_resolve_queue_scope_picks_the_factory_shape(self, db, agent_factory):
        state = SimpleNamespace(claims={}, scopes=[])
        scope = resolve_queue_scope(
            "fx-agent", [agent_factory], db, "owner", None, state=state, context_user_id="alice", session_id="s"
        )
        assert scope["source"] == "factory"
        assert scope["context"]["user_id"] == "alice"
        plain = Agent(id="plain", name="Plain")
        assert resolve_queue_scope("plain", [plain], db, "owner", None, state=state)["source"] == "registry"


class TestWorkerInvokesTheFactoryAgain:
    @pytest.fixture()
    def agent_os(self, db, agent_factory, team_factory):
        return SimpleNamespace(
            queue=QueueConfig(durable=True, db=InMemoryQueueStore()),
            db=db,
            registry=None,
            agents=[agent_factory],
            teams=[team_factory],
            workflows=[],
        )

    @pytest.mark.asyncio
    async def test_worker_rebuilds_the_context_and_resolves(self, agent_os, seen):
        app = SimpleNamespace(state=SimpleNamespace())
        state = SimpleNamespace(claims={"sub": "alice", "org": "acme"}, scopes=["runs:write"])
        scope = factory_queue_scope(state, "alice", "s-1", '{"persona": "pirate"}')
        async with queue_lifespan(app, agent_os):
            worker = get_active_queue_worker()
            assert worker is not None
            resolved = await worker._aresolve_job_component(
                {"component_type": "agent", "component_id": "fx-agent", "payload": {"scope": scope}}
            )
        assert isinstance(resolved, Agent)
        assert resolved.id == "fx-agent"
        assert resolved.instructions == "persona=pirate"
        ctx = seen[-1]
        assert ctx.user_id == "alice"
        assert ctx.session_id == "s-1"
        assert ctx.request is None
        assert ctx.input == Persona(persona="pirate")
        assert ctx.trusted.claims == {"sub": "alice", "org": "acme"}
        assert ctx.trusted.scopes == frozenset({"runs:write"})

    @pytest.mark.asyncio
    async def test_worker_resolves_a_team_factory(self, agent_os):
        app = SimpleNamespace(state=SimpleNamespace())
        scope = factory_queue_scope(SimpleNamespace(), "alice", "t-1", None)
        async with queue_lifespan(app, agent_os):
            worker = get_active_queue_worker()
            assert worker is not None
            resolved = await worker._aresolve_job_component(
                {"component_type": "team", "component_id": "fx-team", "payload": {"scope": scope}}
            )
        assert isinstance(resolved, Team)
        assert resolved.id == "fx-team"
        # The HTTP path's per-request copy sets this; the worker must match
        assert resolved.store_member_responses is True

    @pytest.mark.asyncio
    async def test_ticket_without_the_context_leaves_the_factory_unresolved(self, agent_os, seen):
        app = SimpleNamespace(state=SimpleNamespace())
        async with queue_lifespan(app, agent_os):
            worker = get_active_queue_worker()
            assert worker is not None
            # Registry-sourced (a plain instance was expected) and pre-scope
            # tickets carry no request context: nothing to invoke the factory with
            registry_sourced = await worker._aresolve_job_component(
                {
                    "component_type": "agent",
                    "component_id": "fx-agent",
                    "payload": {"scope": queue_scope(None, None, source="registry")},
                }
            )
            pre_scope = await worker._aresolve_job_component({"component_type": "agent", "component_id": "fx-agent"})
        assert registry_sourced is None
        assert pre_scope is None
        assert seen == []

    @pytest.mark.asyncio
    async def test_factory_ticket_never_runs_a_plain_registry_twin(self, db):
        # A deploy replaced the factory with a plain agent of the same id: the
        # ticket was accepted for a factory-built component, so it must not
        # execute the twin
        plain = Agent(id="fx-agent", name="Plain", db=db)
        agent_os = SimpleNamespace(
            queue=QueueConfig(durable=True, db=InMemoryQueueStore()),
            db=db,
            registry=None,
            agents=[plain],
            teams=[],
            workflows=[],
        )
        app = SimpleNamespace(state=SimpleNamespace())
        scope = factory_queue_scope(SimpleNamespace(), "alice", "s", None)
        async with queue_lifespan(app, agent_os):
            worker = get_active_queue_worker()
            assert worker is not None
            resolved = await worker._aresolve_job_component(
                {"component_type": "agent", "component_id": "fx-agent", "payload": {"scope": scope}}
            )
        assert resolved is None

    @pytest.mark.asyncio
    async def test_factory_refusal_at_claim_time_is_logged_not_raised(self, db, caplog):
        def refuse(ctx):
            raise FactoryValidationError("tenant disabled")

        factory = AgentFactory(id="fx-agent", db=db, factory=refuse)
        context = factory_queue_scope(SimpleNamespace(), "alice", "s", None)["context"]
        assert await aresolve_factory_from_scope(factory, "agent", context) is None
        assert "tenant disabled" in caplog.text
        # No context at all is a corrupt ticket, also unresolved
        assert await aresolve_factory_from_scope(factory, "agent", None) is None

    @pytest.mark.asyncio
    async def test_wrong_component_type_is_refused(self, db, agent_factory):
        context = factory_queue_scope(SimpleNamespace(), "alice", "s", None)["context"]
        assert await aresolve_factory_from_scope(agent_factory, "team", context) is None


class _ScriptedModel(Model):
    def __init__(self):
        super().__init__(id="scripted", name="scripted", provider="test")

    def invoke(self, *args, **kwargs):
        return ModelResponse(role="assistant", content="scripted answer", response_usage=MessageMetrics())

    async def ainvoke(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)

    def invoke_stream(self, *args, **kwargs):
        yield self.invoke(*args, **kwargs)

    async def ainvoke_stream(self, *args, **kwargs):
        yield self.invoke(*args, **kwargs)

    def _parse_provider_response(self, response, **kwargs):
        return response

    def _parse_provider_response_delta(self, response):
        return response


class Required(BaseModel):
    tenant: str


class TestFactoryReadRoutesNeverInvokeTheFactory:
    """Reads only need the run rows in the factory's db. Invoking the factory
    on every poll rebuilt a component per GET, and a factory whose
    input_schema has required fields answered 400 (a GET carries no
    factory_input)."""

    @pytest.fixture()
    def reads(self, db):
        from agno.workflow import Step, Workflow
        from agno.workflow.factory import WorkflowFactory

        invoked: list = []

        def refuse(ctx):
            invoked.append(ctx)
            raise AssertionError("a read must not invoke the factory")

        agent = Agent(id="rx-agent", db=db, model=_ScriptedModel())
        team = Team(
            id="rx-team", db=db, model=_ScriptedModel(), members=[Agent(id="rx-member", model=_ScriptedModel())]
        )
        workflow = Workflow(id="rx-wf", db=db, steps=[Step(name="s", executor=lambda step_input: "step done")])
        runs = {
            "agents/rx-agent": agent.run("hi", session_id="sa").run_id,
            "teams/rx-team": team.run("hi", session_id="st").run_id,
            "workflows/rx-wf": workflow.run("hi", session_id="sw").run_id,
        }
        app = AgentOS(
            agents=[AgentFactory(id="rx-agent", db=db, factory=refuse, input_schema=Required)],
            teams=[TeamFactory(id="rx-team", db=db, factory=refuse, input_schema=Required)],
            workflows=[WorkflowFactory(id="rx-wf", db=db, factory=refuse, input_schema=Required)],
            db=db,
            telemetry=False,
        ).get_app()
        return SimpleNamespace(client=TestClient(app), runs=runs, invoked=invoked)

    @pytest.mark.parametrize(
        "path",
        [
            "/agents/rx-agent/runs?session_id=sa",
            "/agents/rx-agent/runs/{run}?session_id=sa",
            "/agents/rx-agent/runs/{run}/checkpoints?session_id=sa",
            "/teams/rx-team/runs?session_id=st",
            "/teams/rx-team/runs/{run}?session_id=st",
            "/teams/rx-team/runs/{run}/checkpoints?session_id=st",
            "/workflows/rx-wf/runs/{run}?session_id=sw",
        ],
    )
    def test_read_routes_answer_from_the_run_rows(self, reads, path):
        component = "/".join(path.split("/")[1:3])
        run_id = reads.runs[component]
        resp = reads.client.get(path.format(run=run_id))
        assert resp.status_code == 200, resp.text
        assert run_id in resp.text
        assert reads.invoked == []

    @pytest.mark.parametrize("component", ["agents/rx-agent", "teams/rx-team"])
    def test_checkpoint_snapshot_reads_without_the_factory(self, reads, component):
        session = "sa" if component.startswith("agents") else "st"
        run_id = reads.runs[component]
        resp = reads.client.get(f"/{component}/runs/{run_id}/checkpoints/0", params={"session_id": session})
        assert resp.status_code == 200, resp.text
        assert reads.invoked == []


class TestQueueSurfaceRedactsClaims:
    @pytest.fixture()
    def ops(self):
        from fastapi import FastAPI

        from agno.db.schemas.jobs import QueuedJob
        from agno.os.routers.job_queue import get_queue_router

        app = FastAPI()
        app.include_router(get_queue_router(SimpleNamespace()))
        store = InMemoryQueueStore()
        app.state.queue_worker = SimpleNamespace(store=store, config=QueueConfig(durable=True))
        scope = factory_queue_scope(
            SimpleNamespace(claims={"sub": "alice", "email": "alice@acme.io"}, scopes=["runs:write"]),
            "alice",
            "s-1",
            json.dumps({"persona": "pirate"}),
        )
        store._jobs["j1"] = QueuedJob(
            id="j1",
            component_type="agent",
            component_id="fx-agent",
            session_id="s-1",
            payload={"input": "hi", "scope": scope},
        ).to_dict()
        return SimpleNamespace(store=store, client=TestClient(app))

    @pytest.mark.parametrize("path", ["/queue/jobs", "/queue/jobs/j1"])
    def test_claims_never_leave_the_ops_surface(self, ops, path):
        body = ops.client.get(path).json()
        job = body["data"][0] if "data" in body else body
        context = job["payload"]["scope"]["context"]
        assert context["claims"] == "[redacted]"
        assert "alice@acme.io" not in json.dumps(body)
        assert context["input"] == {"persona": "pirate"}, "the rest of the context stays visible to operators"
        assert ops.store._jobs["j1"]["payload"]["scope"]["context"]["claims"]["sub"] == "alice", (
            "the stored ticket keeps the claims the worker needs"
        )
