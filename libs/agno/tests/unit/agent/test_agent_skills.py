"""Tests for Skills integration on Agent.

Mirrors the team skills tests to verify parity:
- Skills tools are registered when agent.skills is set
- Skills tools are absent when agent.skills is None
- Skills system prompt snippet is injected into the system message
- Skills system prompt snippet is omitted when agent.skills is None
- deep_copy shares the Skills instance by reference (shared resource)

The tool registration and prompt injection are hand-maintained sync/async twins on the Agent
(``_tools.get_tools``/``aget_tools``, ``_messages.get_system_message``/``aget_system_message``),
so both variants are asserted.
"""

import json
from unittest.mock import MagicMock

from agno.agent._messages import aget_system_message, get_system_message
from agno.agent._tools import aget_tools, get_tools
from agno.agent.agent import Agent
from agno.models.base import Function
from agno.models.openai import OpenAIResponses
from agno.run.agent import RunOutput
from agno.run.base import RunContext
from agno.session import AgentSession
from agno.skills import DbSkills, LocalSkills, Skills
from agno.tools.function import FunctionCall

SAMPLE_SKILLS_DIR = "cookbook/02_agents/16_skills/sample_skills"

SKILL_TOOL_NAMES = {"get_skill_instructions", "get_skill_reference", "get_skill_script"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_context():
    return RunContext(run_id="test-run", session_id="test-session")


def _make_session():
    return AgentSession(session_id="test-session")


def _make_run_response():
    return RunOutput(run_id="test-run", session_id="test-session", agent_id="test-agent")


def _make_model():
    model = MagicMock()
    model.get_tools_for_api.return_value = []
    model.add_tool.return_value = None
    model.get_instructions_for_model = MagicMock(return_value=None)
    model.get_system_message_for_model = MagicMock(return_value=None)
    return model


def _make_skills():
    return Skills(loaders=[LocalSkills(SAMPLE_SKILLS_DIR)])


def _make_agent(*, with_skills: bool) -> Agent:
    agent = Agent(name="test-agent", skills=_make_skills() if with_skills else None)
    agent.model = _make_model()
    return agent


def _get_skill_tools(tools):
    return [t for t in tools if isinstance(t, Function) and t.name in SKILL_TOOL_NAMES]


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------


def test_skills_tools_registered_when_skills_set():
    """Skills tools are present in the tool list when agent.skills is set."""
    tools = get_tools(
        agent=_make_agent(with_skills=True),
        run_response=_make_run_response(),
        run_context=_make_run_context(),
        session=_make_session(),
    )

    assert {t.name for t in _get_skill_tools(tools)} == SKILL_TOOL_NAMES


async def test_askills_tools_registered_when_skills_set():
    """Async twin: skills tools are present in the tool list when agent.skills is set."""
    tools = await aget_tools(
        agent=_make_agent(with_skills=True),
        run_response=_make_run_response(),
        run_context=_make_run_context(),
        session=_make_session(),
    )

    assert {t.name for t in _get_skill_tools(tools)} == SKILL_TOOL_NAMES


def test_skills_tools_absent_when_skills_none():
    """No skills tools are present when agent.skills is None."""
    tools = get_tools(
        agent=_make_agent(with_skills=False),
        run_response=_make_run_response(),
        run_context=_make_run_context(),
        session=_make_session(),
    )

    assert _get_skill_tools(tools) == []


# ---------------------------------------------------------------------------
# System message tests
# ---------------------------------------------------------------------------


def test_system_message_contains_skills_snippet():
    """System message includes the snippet verbatim when agent.skills is set."""
    agent = _make_agent(with_skills=True)

    msg = get_system_message(agent, _make_session())

    assert msg is not None
    assert agent.skills.get_system_prompt_snippet() in msg.content


async def test_asystem_message_contains_skills_snippet():
    """Async twin: system message includes the snippet verbatim when agent.skills is set."""
    agent = _make_agent(with_skills=True)

    msg = await aget_system_message(agent, _make_session())

    assert msg is not None
    assert agent.skills.get_system_prompt_snippet() in msg.content


def test_system_message_omits_skills_when_none():
    """System message does not contain skills block when agent.skills is None."""
    msg = get_system_message(_make_agent(with_skills=False), _make_session())

    if msg is not None:
        assert "<skills_system>" not in msg.content


# ---------------------------------------------------------------------------
# Deep copy tests
# ---------------------------------------------------------------------------


def test_deep_copy_shares_skills_by_reference():
    """deep_copy should share the Skills instance (heavy resource), not duplicate it."""
    skills = _make_skills()
    agent = Agent(name="test-agent", skills=skills)

    assert agent.deep_copy().skills is skills


# ---------------------------------------------------------------------------
# Per-user skills on the message path (the run's user reaches the loader)
# ---------------------------------------------------------------------------


def _make_db(tmp_path):
    from agno.db.sqlite import SqliteDb

    return SqliteDb(db_file=str(tmp_path / "agent-skills.db"))


def _create_skill_row(db, name: str = "release-notes"):
    db.create_skill(
        {
            "name": name,
            "description": f"Skill {name}",
            "instructions": f"Instructions for {name}.",
            "scripts": {"draft.sh": "#!/bin/sh\necho draft\n"},
            "references": {"style.md": "Keep it short.\n"},
        }
    )


def _seed_owned_rows(db):
    db.create_skill({"name": "alice-skill", "description": "d", "instructions": "i", "user_id": "alice"})
    db.create_skill({"name": "bob-skill", "description": "d", "instructions": "i", "user_id": "bob"})
    db.create_skill({"name": "shared-skill", "description": "d", "instructions": "i"})


def _skill_instructions(agent: Agent, run_context: RunContext, skill_name: str) -> dict:
    """Call get_skill_instructions the way a run does: through FunctionCall, context injected."""
    tool = next(f for f in agent.skills.get_tools() if f.name == "get_skill_instructions")
    tool._run_context = run_context
    call = FunctionCall(function=tool, arguments={"skill_name": skill_name})
    assert call.execute().status == "success"
    return json.loads(call.result)


def test_two_users_interleaved_requests_keep_their_own_skills(tmp_path):
    """deep_copy shares the Skills object, which is what every AgentOS route does per request:
    alice's prompt, bob's on the copy, then alice's tool call must still find her skill."""
    db = _make_db(tmp_path)
    _seed_owned_rows(db)
    # A real model, never invoked: deep_copy rejects the mock the other tests use.
    agent = Agent(name="test-agent", model=OpenAIResponses(id="gpt-5.5"), skills=Skills(loaders=[DbSkills(db)]))
    fresh = agent.deep_copy()
    assert fresh.skills is agent.skills

    alice = RunContext(run_id="r-alice", session_id="s", user_id="alice")
    bob = RunContext(run_id="r-bob", session_id="s", user_id="bob")
    for _ in range(2):
        alice_prompt = get_system_message(agent, _make_session(), run_context=alice).content
        bob_prompt = get_system_message(fresh, _make_session(), run_context=bob).content
        assert "alice-skill" in alice_prompt and "bob-skill" not in alice_prompt
        assert "bob-skill" in bob_prompt and "alice-skill" not in bob_prompt

        assert _skill_instructions(agent, alice, "alice-skill")["skill_name"] == "alice-skill"
        assert "not found" in _skill_instructions(fresh, bob, "alice-skill")["error"]


async def test_two_users_interleaved_requests_keep_their_own_skills_async(tmp_path):
    db = _make_db(tmp_path)
    _seed_owned_rows(db)
    agent = Agent(name="test-agent", model=OpenAIResponses(id="gpt-5.5"), skills=Skills(loaders=[DbSkills(db)]))
    fresh = agent.deep_copy()

    alice = RunContext(run_id="r-alice", session_id="s", user_id="alice")
    bob = RunContext(run_id="r-bob", session_id="s", user_id="bob")
    for _ in range(2):
        alice_prompt = (await aget_system_message(agent, _make_session(), run_context=alice)).content
        bob_prompt = (await aget_system_message(fresh, _make_session(), run_context=bob)).content
        assert "alice-skill" in alice_prompt and "bob-skill" not in alice_prompt
        assert "bob-skill" in bob_prompt and "alice-skill" not in bob_prompt

        assert _skill_instructions(agent, alice, "alice-skill")["skill_name"] == "alice-skill"
        assert "not found" in _skill_instructions(fresh, bob, "alice-skill")["error"]


async def test_asystem_message_refreshes_skills_through_async_db(tmp_path):
    """The async message path reads an async backend through its awaited skills method.

    AsyncSqliteDb has no sync skills read at all, so the snippet appearing in the
    system message proves the refresh went through the awaited async method.
    """
    from agno.db.sqlite.async_sqlite import AsyncSqliteDb

    db = AsyncSqliteDb(db_file=str(tmp_path / "agent-skills-async.db"))
    await db.create_skill({"name": "async-skill", "description": "d", "instructions": "i"})

    agent = Agent(name="test-agent", skills=Skills(loaders=[DbSkills(db)]))
    agent.model = _make_model()
    msg = await aget_system_message(agent, _make_session())

    assert msg is not None
    assert "async-skill" in msg.content
