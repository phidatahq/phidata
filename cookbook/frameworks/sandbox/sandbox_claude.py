"""The smallest sandboxed Claude agent: two turns, each on a fresh computer, no AgentOS.

Build the runtime image, run Postgres, export ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN:

    .venv/bin/python cookbook/frameworks/sandbox/build_image.py --tag agno-sandbox:local
    ./cookbook/scripts/run_pgvector.sh
    .venv/bin/python cookbook/frameworks/sandbox/sandbox_claude.py
"""

import os
from uuid import uuid4

from agno.agents.claude import ClaudeAgent
from agno.db.postgres import PostgresDb
from agno.sandbox.docker import DockerSandbox

credentials = {
    key: os.environ[key]
    for key in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
    if key in os.environ
}
if not credentials:
    raise SystemExit(
        "Export ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN for the container"
    )

agent = ClaudeAgent(
    id="coder",
    model="claude-sonnet-4-6",
    # The container is the boundary, so Claude may run what it writes without asking.
    permission_mode="bypassPermissions",
    db=PostgresDb(
        db_url=os.environ.get(
            "AGNO_TEST_SANDBOX_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
        )
    ),
    # Every turn runs inside a computer from this sandbox. Checkpoints default to
    # ~/.agno/sandbox/checkpoints, fine for one process on one machine.
    sandbox=DockerSandbox(
        os.environ.get("AGNO_SANDBOX_IMAGE", "agno-sandbox:local"),
        network="isolated",
        memory_mb=1024,
        env=credentials,
    ),
)

# A session that already has turns from outside a sandbox cannot be moved into one, so this
# example always starts a fresh session.
session_id = "demo-" + uuid4().hex[:8]
first = agent.run(
    "Write hello.py that prints hello, run it, and tell me the output.",
    session_id=session_id,
)
print("turn 1:", first.status, first.content)

# The container from turn 1 is gone. This turn restores the checkpoint into a new one and
# continues the same Claude session.
second = agent.run(
    "What did you create in the previous turn? One sentence.", session_id=session_id
)
print("turn 2:", second.status, second.content)
