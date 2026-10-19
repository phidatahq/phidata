"""``store_run=False`` runs an agent, team or workflow without writing the run or its session.

The run still reads the existing session (history, state) but works on a private copy:
nothing is written back, and a cached session is not changed by the temporary run.
"""

from typing import Any, Dict, List, Optional

import pytest

from agno.agent.agent import Agent
from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb
from agno.models.base import Model
from agno.models.message import MessageMetrics
from agno.models.response import ModelResponse
from agno.session.agent import AgentSession
from agno.session.team import TeamSession
from agno.session.workflow import WorkflowSession
from agno.team.team import Team
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow


class RecordingModel(Model):
    """A model that answers without a provider call and records the messages it was given."""

    def __init__(self, reply: str = "an answer"):
        super().__init__(id="recording", name="recording", provider="test")
        self._reply = reply
        self.calls: List[List[Any]] = []

    def _resp(self, **kwargs) -> ModelResponse:
        self.calls.append(list(kwargs.get("messages") or []))
        return ModelResponse(content=self._reply, role="assistant", response_usage=MessageMetrics())

    def invoke(self, *args, **kwargs):
        return self._resp(**kwargs)

    async def ainvoke(self, *args, **kwargs):
        return self._resp(**kwargs)

    def invoke_stream(self, *args, **kwargs):
        yield self._resp(**kwargs)

    async def ainvoke_stream(self, *args, **kwargs):
        yield self._resp(**kwargs)

    def parse_args(self, *args, **kwargs):
        return {}

    def _parse_provider_response(self, response, **kwargs):
        return response

    def _parse_provider_response_delta(self, response):
        return response


@pytest.fixture()
def db(tmp_path) -> SqliteDb:
    return SqliteDb(db_file=str(tmp_path / "store_run.db"))


def _runs(db: SqliteDb, session_id: str) -> int:
    runs = db.get_runs(session_id=session_id)
    assert isinstance(runs, list)
    return len(runs)


def _user_contents(messages: List[Any]) -> List[Optional[str]]:
    return [m.content for m in messages if getattr(m, "role", None) == "user"]


class TestAgent:
    def test_sync_temporary_run_writes_nothing(self, db: SqliteDb):
        agent = Agent(id="a", model=RecordingModel(), db=db)

        output = agent.run("hi", session_id="s1", store_run=False)

        assert output.content == "an answer"
        assert db.get_session(session_id="s1", session_type=SessionType.AGENT) is None
        assert _runs(db, "s1") == 0

        # The default keeps storing.
        agent.run("hi again", session_id="s1")
        assert db.get_session(session_id="s1", session_type=SessionType.AGENT) is not None
        assert _runs(db, "s1") == 1

    @pytest.mark.asyncio
    async def test_async_temporary_run_writes_nothing(self, db: SqliteDb):
        agent = Agent(id="a", model=RecordingModel(), db=db)

        output = await agent.arun("hi", session_id="s1", store_run=False)
        assert output.content == "an answer"

        events = [event async for event in agent.arun("hi", session_id="s1", stream=True, store_run=False)]
        assert events

        assert db.get_session(session_id="s1", session_type=SessionType.AGENT) is None
        assert _runs(db, "s1") == 0

    def test_temporary_run_sees_history_but_does_not_extend_it(self, db: SqliteDb):
        model = RecordingModel()
        agent = Agent(id="a", model=model, db=db, add_history_to_context=True)

        agent.run("first", session_id="s1")
        agent.run("second", session_id="s1", store_run=False)
        agent.run("third", session_id="s1")

        # The temporary run was prompted with the stored history ...
        assert _user_contents(model.calls[1]) == ["first", "second"]
        # ... but the next stored run never saw the temporary one.
        assert _user_contents(model.calls[2]) == ["first", "third"]
        assert _runs(db, "s1") == 2

    def test_cached_session_is_not_changed_by_a_temporary_run(self, db: SqliteDb):
        agent = Agent(id="a", model=RecordingModel(), db=db, cache_session=True)

        agent.run("first", session_id="s1")
        cached = agent._get_cached_session("s1")
        assert cached is not None and len(cached.runs or []) == 1

        agent.run("second", session_id="s1", store_run=False)

        assert agent._get_cached_session("s1") is cached
        assert len(cached.runs or []) == 1
        assert cached.transient is False
        assert _runs(db, "s1") == 1

    def test_introduction_is_not_written_for_a_temporary_run(self, db: SqliteDb):
        agent = Agent(id="a", model=RecordingModel(), db=db, introduction="Hello there")

        agent.run("hi", session_id="s1", store_run=False)

        assert db.get_session(session_id="s1", session_type=SessionType.AGENT) is None
        assert _runs(db, "s1") == 0

    def test_background_rejects_store_run_false(self, db: SqliteDb):
        agent = Agent(id="a", model=RecordingModel(), db=db)

        with pytest.raises(ValueError, match="store_run=False"):
            agent.arun("hi", session_id="s1", background=True, store_run=False)

    def test_run_context_carries_the_option(self, db: SqliteDb):
        seen: Dict[str, Any] = {}

        def record(run_context) -> None:
            seen["store_run"] = run_context.store_run

        agent = Agent(id="a", model=RecordingModel(), db=db, pre_hooks=[record])
        agent.run("hi", session_id="s1", store_run=False)
        assert seen["store_run"] is False

        agent.run("hi", session_id="s1")
        assert seen["store_run"] is True


class TestTeam:
    def test_temporary_run_writes_neither_team_nor_member_rows(self, db: SqliteDb):
        model = RecordingModel()
        member = Agent(id="member", name="Member", model=model)
        team = Team(id="t", name="T", model=model, members=[member], db=db)

        output = team.run("hi", session_id="s1", store_run=False)

        assert output.content == "an answer"
        assert db.get_session(session_id="s1", session_type=SessionType.TEAM) is None
        assert _runs(db, "s1") == 0

        team.run("hi", session_id="s1")
        assert db.get_session(session_id="s1", session_type=SessionType.TEAM) is not None
        assert _runs(db, "s1") >= 1

    @pytest.mark.asyncio
    async def test_async_temporary_run_writes_nothing(self, db: SqliteDb):
        model = RecordingModel()
        member = Agent(id="member", name="Member", model=model)
        team = Team(id="t", name="T", model=model, members=[member], db=db)

        output = await team.arun("hi", session_id="s1", store_run=False)
        assert output.content == "an answer"
        assert db.get_session(session_id="s1", session_type=SessionType.TEAM) is None
        assert _runs(db, "s1") == 0

    def test_background_rejects_store_run_false(self, db: SqliteDb):
        model = RecordingModel()
        team = Team(id="t", name="T", model=model, members=[Agent(id="member", model=model)], db=db)

        with pytest.raises(ValueError, match="store_run=False"):
            team.arun("hi", session_id="s1", background=True, store_run=False)


class TestWorkflow:
    def _workflow(self, db: SqliteDb) -> Workflow:
        step_agent = Agent(id="step-agent", name="StepAgent", model=RecordingModel())
        return Workflow(id="w", name="W", steps=[Step(name="s1", agent=step_agent)], db=db)

    def test_sync_temporary_run_writes_nothing(self, db: SqliteDb):
        workflow = self._workflow(db)

        output = workflow.run("hi", session_id="s1", store_run=False)

        assert output.content == "an answer"
        assert db.get_session(session_id="s1", session_type=SessionType.WORKFLOW) is None
        assert _runs(db, "s1") == 0

        workflow.run("hi", session_id="s1")
        assert db.get_session(session_id="s1", session_type=SessionType.WORKFLOW) is not None
        assert _runs(db, "s1") == 1

    @pytest.mark.asyncio
    async def test_async_temporary_run_writes_nothing(self, db: SqliteDb):
        workflow = self._workflow(db)

        output = await workflow.arun("hi", session_id="s1", store_run=False)
        assert output.content == "an answer"

        events = [event async for event in workflow.arun("hi", session_id="s1", stream=True, store_run=False)]
        assert events

        assert db.get_session(session_id="s1", session_type=SessionType.WORKFLOW) is None
        assert _runs(db, "s1") == 0

    def test_background_rejects_store_run_false(self, db: SqliteDb):
        workflow = self._workflow(db)

        with pytest.raises(ValueError, match="store_run=False"):
            workflow.arun("hi", session_id="s1", background=True, store_run=False)


class TestTransientMarkerStaysOutOfStorage:
    @pytest.mark.parametrize("session_cls", [AgentSession, TeamSession, WorkflowSession])
    def test_to_dict_omits_the_marker(self, session_cls):
        session = session_cls(session_id="s1")
        session.transient = True

        assert "transient" not in session.to_dict()
        restored = session_cls.from_dict(session.to_dict())
        assert restored is not None and restored.transient is False
