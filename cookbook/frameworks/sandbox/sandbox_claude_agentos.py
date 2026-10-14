"""The smallest sandboxed Claude agent served by AgentOS, with a durable queue.

Same agent as sandbox_claude.py. AgentOS adds the HTTP API, the durable queue that runs each
turn on a worker, and Redis for cancellation and event streaming, so any replica can answer a
request and a turn survives the request that started it.

Build the runtime image, run Postgres and Redis, export ANTHROPIC_API_KEY or
CLAUDE_CODE_OAUTH_TOKEN, then:

    .venv/bin/python cookbook/frameworks/sandbox/sandbox_claude_agentos.py

Start a turn in the background and keep the run id it returns:

    curl -X POST http://localhost:7777/agents/coder/runs \
      -F session_id=demo -F message='Write hello.py that prints hello and run it' \
      -F stream=false -F background=true

Poll it, or stream the next turn on the same session:

    curl "http://localhost:7777/agents/coder/runs/<run_id>?session_id=demo"
    curl -N -X POST http://localhost:7777/agents/coder/runs \
      -F session_id=demo -F message='What did you create? One sentence.' -F stream=true
"""

import os
from pathlib import Path

from agno.agents.claude import ClaudeAgent
from agno.db.postgres import PostgresDb
from agno.job_queue.config import QueueConfig, RedisCoordination
from agno.os import AgentOS
from agno.sandbox.checkpoint import FileCheckpointStore
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

db = PostgresDb(
    db_url=os.environ.get(
        "AGNO_TEST_SANDBOX_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
    )
)
agent = ClaudeAgent(
    id="coder",
    model="claude-sonnet-4-6",
    # The container is the boundary, so Claude may run what it writes without asking.
    permission_mode="bypassPermissions",
    sandbox=DockerSandbox(
        os.environ.get("AGNO_SANDBOX_IMAGE", "agno-sandbox:local"),
        network="isolated",
        memory_mb=1024,
        env=credentials,
        # With several replicas, point this at storage every replica can read.
        checkpoints=FileCheckpointStore(
            Path.home() / ".agno" / "sandbox" / "checkpoints"
        ),
    ),
)
agent_os = AgentOS(
    id="sandbox-claude",
    agents=[agent],
    db=db,
    queue=QueueConfig(
        durable=True,
        db=db,
        redis=RedisCoordination(
            url=os.environ.get("AGNO_TEST_REDIS_URL", "redis://localhost:6379/0")
        ),
    ),
    telemetry=False,
)

if __name__ == "__main__":
    agent_os.serve(
        app=agent_os.get_app(),
        port=int(os.environ.get("AGNO_SANDBOX_PORT", "7777")),
        reload=False,
    )
