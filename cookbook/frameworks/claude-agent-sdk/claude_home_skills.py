"""
ClaudeAgent: Agno Skills and Memories in the Harness Home
=========================================================
Agno owns the skills and the user memories. Before each run the adapter writes
them into the agent's config_dir, where Claude Code discovers skills natively
(skills/<name>/SKILL.md) and reads CLAUDE.md as user-level instructions.

The run asks Claude to use the code-review skill and to greet the user by a
name that only exists in Agno's memory table. The script fails if the answer
misses the name or no Skill call was made.

The scratch home needs its own login. Export ANTHROPIC_API_KEY, or run once:

    CLAUDE_CONFIG_DIR=tmp/harnesses/claude/home claude login

See README.md for setup.
"""

import os
from pathlib import Path

from agno.agents.claude import ClaudeAgent
from agno.db.schemas.memory import UserMemory
from agno.db.sqlite import SqliteDb
from agno.memory.manager import MemoryManager
from agno.skills import LocalSkills, Skills

# ---------------------------------------------------------------------------
# Configure the Example
# ---------------------------------------------------------------------------
repo = Path(__file__).resolve().parents[3]
workspace = repo / "cookbook/frameworks/sample_project"
state_dir = Path(os.getenv("HARNESS_STATE_DIR", "tmp/harnesses/claude"))
config_dir = state_dir / "home"
db = SqliteDb(db_file=str(state_dir / "home_skills.db"))
memory = MemoryManager(db=db)
user_id = "sam"
prompt = (
    "Use the code-review skill: tell me the first heading of its instructions. "
    "Then greet me by my name in one sentence. Do not read any other files."
)

# ---------------------------------------------------------------------------
# Create the Agent
# ---------------------------------------------------------------------------
agent = ClaudeAgent(
    id="claude-home-skills",
    model="claude-sonnet-5-5",
    cwd=str(workspace),
    config_dir=config_dir,
    agno_skills=Skills(
        loaders=[LocalSkills(str(repo / "cookbook/02_agents/16_skills/sample_skills"))]
    ),
    db=db,
    memory_manager=memory,
    add_memories_to_context=True,
    tools=["Skill", "Read"],
    setting_sources=["user"],
    strict_mcp_config=True,
)

# ---------------------------------------------------------------------------
# Run the Agent
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not memory.get_user_memories(user_id=user_id):
        memory.add_user_memory(
            UserMemory(memory="The user's name is Sam."), user_id=user_id
        )

    result = agent.print_response(prompt, stream=True, user_id=user_id)

    skills_written = sorted(
        p.name for p in (config_dir / "skills").iterdir() if (p / "SKILL.md").is_file()
    )
    tools_used = [tool.tool_name for tool in result.tools or []]
    print(f"\nSkills in {config_dir.resolve()}: {skills_written}")
    print(f"Tools used: {tools_used}")
    print(f"CLAUDE.md block:\n{(config_dir / 'CLAUDE.md').read_text()}")
    if "Sam" not in str(result.content):
        raise SystemExit("The answer did not use the memory written into CLAUDE.md.")
    if "Skill" not in tools_used:
        raise SystemExit(
            "Claude did not call the Skill tool for the materialized skill."
        )
    print("Memory and skill both came from Agno and were picked up by Claude Code.")
