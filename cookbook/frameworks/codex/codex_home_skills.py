"""
CodexAgent: Agno Skills and Memories in the Harness Home
========================================================
Agno owns the skills and the user memories. Before each run the adapter writes
them into the agent's codex_home, where Codex discovers skills natively
(skills/<name>/SKILL.md) and reads AGENTS.md as user-level instructions.

The run asks Codex to use the code-review skill and to greet the user by a
name that only exists in Agno's memory table. The script fails if the answer
misses the name or the skill.

The scratch home needs its own login. With OPENAI_API_KEY exported the script
logs the scratch home in through the agent on first use. Otherwise run once:

    CODEX_HOME=tmp/harnesses/codex/home codex login

See README.md for setup.
"""

import os
from pathlib import Path

from agno.agents.codex import CodexAgent
from agno.db.schemas.memory import UserMemory
from agno.db.sqlite import SqliteDb
from agno.memory.manager import MemoryManager
from agno.skills import LocalSkills, Skills

# ---------------------------------------------------------------------------
# Configure the Example
# ---------------------------------------------------------------------------
repo = Path(__file__).resolve().parents[3]
workspace = repo / "cookbook/frameworks/sample_project"
state_dir = Path(os.getenv("HARNESS_STATE_DIR", "tmp/harnesses/codex"))
codex_home = state_dir / "home"
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
agent = CodexAgent(
    id="codex-home-skills",
    model=os.getenv("CODEX_MODEL", "gpt-5.6-luna"),
    cwd=str(workspace),
    codex_home=codex_home,
    agno_skills=Skills(
        loaders=[LocalSkills(str(repo / "cookbook/02_agents/16_skills/sample_skills"))]
    ),
    db=db,
    memory_manager=memory,
    add_memories_to_context=True,
    sandbox="read-only",
    approval_mode="deny_all",
    reasoning_effort="low",
)

# ---------------------------------------------------------------------------
# Run the Agent
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and not (codex_home / "auth.json").exists():
        agent.login_api_key(api_key)
    if not memory.get_user_memories(user_id=user_id):
        memory.add_user_memory(
            UserMemory(memory="The user's name is Sam."), user_id=user_id
        )

    result = agent.print_response(prompt, stream=True, user_id=user_id)

    skills_written = sorted(
        p.name for p in (codex_home / "skills").iterdir() if (p / "SKILL.md").is_file()
    )
    tools_used = [tool.tool_name for tool in result.tools or []]
    print(f"\nSkills in {codex_home.resolve()}: {skills_written}")
    print(f"Tools used: {tools_used}")
    print(f"AGENTS.md block:\n{(codex_home / 'AGENTS.md').read_text()}")
    if "Sam" not in str(result.content):
        raise SystemExit("The answer did not use the memory written into AGENTS.md.")
    if "code-review" not in str(result.content).lower() and not tools_used:
        raise SystemExit("Codex did not use the materialized skill.")
    print("Memory and skill both came from Agno and were picked up by Codex.")
