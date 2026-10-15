"""A sandboxed Claude agent behind AgentOS with a durable queue: the same agent as
sandbox_claude.py, served over HTTP.

Build the runtime image, run Postgres and Redis, and export ANTHROPIC_API_KEY or
CLAUDE_CODE_OAUTH_TOKEN:

    .venv/bin/python cookbook/frameworks/sandbox/build_image.py --tag agno-sandbox:local
    ./cookbook/scripts/run_pgvector.sh
    docker run -d --name agno-redis -p 6379:6379 redis
    .venv/bin/python cookbook/frameworks/sandbox/sandbox_claude_agentos.py

Then send a turn and poll it:

    curl -X POST localhost:7777/agents/coder/runs \\
        -F session_id=demo -F background=true -F message="Write hello.py and run it"
    curl localhost:7777/agents/coder/runs/<run_id>?session_id=demo

Every API request submits to the queue, so a dropped connection does not cancel the turn, and a
second request on the same session waits for the first. The checkpoint store is named explicitly:
with a queue, any replica may run the next attempt, so checkpoints must live where every replica
can read them.
"""

import os
from pathlib import Path

from agno.agents.claude import ClaudeAgent
from agno.db.postgres import PostgresDb
from agno.job_queue.config import QueueConfig, RedisCoordination
from agno.os import AgentOS
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandbox

db = PostgresDb(
    db_url=os.getenv(
        "AGNO_SANDBOX_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
    )
)
agent = ClaudeAgent(
    id="coder",
    model="claude-sonnet-4-6",
    permission_mode="bypassPermissions",
    sandbox=DockerSandbox(
        os.getenv("AGNO_SANDBOX_IMAGE", "agno-sandbox:local"),
        network="isolated",
        memory_mb=1024,
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
            url=os.getenv("AGNO_SANDBOX_REDIS_URL", "redis://localhost:6379/0")
        ),
    ),
    telemetry=False,
)

if __name__ == "__main__":
    agent_os.serve(
        app=agent_os.get_app(),
        port=int(os.getenv("AGNO_SANDBOX_PORT", "7777")),
        reload=False,
    )
