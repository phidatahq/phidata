"""Agno skills and user memories written into a harness home, without model calls."""

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Optional

import pytest

from agno.agents._home import (
    BLOCK_END,
    BLOCK_START,
    materialize_skills,
    memories_block,
    remove_materialized_skills,
    write_managed_block,
)
from agno.agents.claude import ClaudeAgent
from agno.agents.claude import agent as claude_module
from agno.agents.codex import CodexAgent
from agno.db.schemas.memory import UserMemory
from agno.memory.manager import MemoryManager
from agno.skills import LocalSkills, Skills
from agno.skills.skill import Skill

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def write_skill(root, name, description="Review code", scripts=(), references=()):
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n---\n\nUse {name}.\n")
    for script in scripts:
        (folder / "scripts").mkdir(exist_ok=True)
        (folder / "scripts" / script).write_text("print('hi')\n")
    for reference in references:
        (folder / "references").mkdir(exist_ok=True)
        (folder / "references" / reference).write_text("# notes\n")
    return folder


@pytest.fixture
def skills(tmp_path):
    source = tmp_path / "source"
    write_skill(source, "code-review", scripts=["lint.py"], references=["checklist.md"])
    write_skill(source, "git-workflow")
    return Skills(loaders=[LocalSkills(str(source))])


@dataclass
class Options:
    model: Optional[str] = None
    cwd: Any = None
    tools: Any = None
    allowed_tools: list = field(default_factory=list)
    setting_sources: Any = None
    skills: Any = None
    env: dict = field(default_factory=dict)
    extra_args: dict = field(default_factory=dict)
    resume: Optional[str] = None
    session_id: Optional[str] = None
    continue_conversation: bool = False
    fork_session: bool = False
    include_partial_messages: bool = False
    session_store: Any = None
    enable_file_checkpointing: bool = False


@pytest.fixture
def claude_sdk(monkeypatch):
    monkeypatch.setattr(claude_module, "_sdk", lambda: SimpleNamespace(ClaudeAgentOptions=Options))


# ---------------------------------------------------------------------------
# Skills on disk
# ---------------------------------------------------------------------------


def test_skills_are_written_in_the_skill_md_layout(tmp_path, skills):
    home = tmp_path / "home"
    assert materialize_skills(home, skills) == ["code-review", "git-workflow"]
    skill_md = (home / "skills" / "code-review" / "SKILL.md").read_text()
    assert skill_md.startswith("---\nname: code-review\ndescription: Review code\n---\n")
    assert "Use code-review." in skill_md
    assert (home / "skills" / "code-review" / "scripts" / "lint.py").is_file()
    assert (home / "skills" / "code-review" / "references" / "checklist.md").is_file()
    assert json.loads((home / ".agno" / "skills.json").read_text()) == ["code-review", "git-workflow"]


def test_stale_agno_skills_are_removed_and_foreign_folders_kept(tmp_path, skills):
    home = tmp_path / "home"
    materialize_skills(home, skills)
    foreign = home / "skills" / "hand-made"
    foreign.mkdir()
    (foreign / "SKILL.md").write_text("mine")
    fewer = Skills(loaders=[])
    fewer._skills = {"git-workflow": skills.get_skill("git-workflow")}
    assert materialize_skills(home, fewer) == ["git-workflow"]
    assert not (home / "skills" / "code-review").exists()
    assert (foreign / "SKILL.md").read_text() == "mine"
    remove_materialized_skills(home)
    assert not (home / "skills" / "git-workflow").exists()
    assert (foreign / "SKILL.md").is_file()


def test_a_folder_agno_did_not_write_is_not_overwritten(tmp_path, skills):
    home = tmp_path / "home"
    existing = home / "skills" / "code-review"
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("hand-written")
    assert materialize_skills(home, skills) == ["git-workflow"]
    assert (existing / "SKILL.md").read_text() == "hand-written"


def test_skill_without_source_folder_still_writes_instructions(tmp_path):
    only = Skills(loaders=[])
    only._skills = {"db-skill": Skill(name="db-skill", description="From the db", instructions="Body", source_path="")}
    home = tmp_path / "home"
    assert materialize_skills(home, only) == ["db-skill"]
    assert "Body" in (home / "skills" / "db-skill" / "SKILL.md").read_text()


# ---------------------------------------------------------------------------
# Managed instructions block
# ---------------------------------------------------------------------------


def test_managed_block_is_added_replaced_and_removed_around_user_content(tmp_path):
    path = tmp_path / "CLAUDE.md"
    path.write_text("# Mine\n\nKeep this.\n")
    write_managed_block(path, "first")
    text = path.read_text()
    assert text.startswith("# Mine\n\nKeep this.\n\n" + BLOCK_START)
    assert text.endswith(BLOCK_END + "\n")
    write_managed_block(path, "second")
    text = path.read_text()
    assert "first" not in text and "second" in text and text.count(BLOCK_START) == 1
    write_managed_block(path, None)
    assert path.read_text() == "# Mine\n\nKeep this.\n"


def test_managed_block_alone_creates_and_deletes_the_file(tmp_path):
    path = tmp_path / "AGENTS.md"
    write_managed_block(path, None)
    assert not path.exists()
    write_managed_block(path, "only agno")
    assert path.read_text() == f"{BLOCK_START}\nonly agno\n{BLOCK_END}\n"
    write_managed_block(path, None)
    assert not path.exists()


def test_memories_block_lists_each_memory():
    assert memories_block([]) is None
    block = memories_block([UserMemory(memory="Prefers British spelling"), UserMemory(memory="Name is Sam")])
    assert block.startswith("## What you remember about this user")
    assert "- Prefers British spelling\n- Name is Sam" in block


# ---------------------------------------------------------------------------
# Adapter wiring
# ---------------------------------------------------------------------------


def test_home_state_requires_the_home_directory_parameter(claude_sdk, skills):
    with pytest.raises(ValueError, match="set config_dir"):
        ClaudeAgent(agno_skills=skills)
    with pytest.raises(ValueError, match="set codex_home"):
        CodexAgent(add_memories_to_context=True, db=object())
    with pytest.raises(ValueError, match="memory_manager or db"):
        CodexAgent(codex_home="x", add_memories_to_context=True)


@pytest.mark.asyncio
async def test_claude_materializes_skills_and_memories_before_the_query(claude_sdk, tmp_path, skills, monkeypatch):
    home = tmp_path / "home"
    (home).mkdir()
    (home / "CLAUDE.md").write_text("# Team rules\n")
    manager = MemoryManager()
    monkeypatch.setattr(
        manager, "aget_user_memories", lambda user_id=None: _async([UserMemory(memory=f"User is {user_id}")])
    )
    agent = ClaudeAgent(
        config_dir=home, agno_skills=skills, memory_manager=manager, add_memories_to_context=True, tools=["Skill"]
    )
    seen = {}

    async def query(input, history, **kwargs):
        seen["skills"] = kwargs.get("materialized_skills")
        seen["options"] = agent._build_options(skills=kwargs.get("materialized_skills"))
        yield "ok"

    monkeypatch.setattr(agent, "_aquery_sdk", query)
    messages = [m async for m in agent._aquery("hi", None, streaming=False, run_id="r1", user_id="sam")]
    assert messages == ["ok"]
    assert seen["skills"] == ["code-review", "git-workflow"]
    assert seen["options"].skills == ["code-review", "git-workflow"]
    assert (home / "skills" / "code-review" / "SKILL.md").is_file()
    claude_md = (home / "CLAUDE.md").read_text()
    assert claude_md.startswith("# Team rules\n") and "- User is sam" in claude_md


def test_claude_keeps_an_explicit_skill_selection(claude_sdk, tmp_path, skills):
    agent = ClaudeAgent(config_dir=tmp_path, agno_skills=skills, skills=["code-review"])
    assert agent._build_options(skills=["code-review", "git-workflow"]).skills == ["code-review"]
    assert ClaudeAgent(config_dir=tmp_path)._build_options(skills=[]).skills is None


@pytest.mark.asyncio
async def test_codex_materializes_into_agents_md(tmp_path, skills, monkeypatch):
    home = tmp_path / "home"
    manager = MemoryManager()
    monkeypatch.setattr(manager, "aget_user_memories", lambda user_id=None: _async([UserMemory(memory="Likes tea")]))
    agent = CodexAgent(codex_home=home, agno_skills=skills, memory_manager=manager, add_memories_to_context=True)
    assert await agent._amaterialize_home("AGENTS.md", "sam") == ["code-review", "git-workflow"]
    assert (home / "skills" / "git-workflow" / "SKILL.md").is_file()
    assert "- Likes tea" in (home / "AGENTS.md").read_text()
    monkeypatch.setattr(manager, "aget_user_memories", lambda user_id=None: _async([]))
    await agent._amaterialize_home("AGENTS.md", "sam")
    assert not (home / "AGENTS.md").exists()


async def _async(value):
    return value
