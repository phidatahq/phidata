"""A sandboxed Claude agent on Modal behind AgentOS with a durable queue. This creates billable compute.

The same agent as sandbox_claude_modal.py, served over HTTP like sandbox_claude_agentos.py. Sign
in to Modal (modal token new), export ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN, and run
Postgres and Redis:

    ./cookbook/scripts/run_pgvector.sh
    docker run -d --name agno-redis -p 6379:6379 redis
    .venv/bin/python cookbook/frameworks/sandbox/modal/sandbox_claude_modal_agentos.py

Then send a turn and poll it:

    curl -X POST localhost:7777/agents/coder/runs \\
        -F session_id=demo -F background=true -F message="Write hello.py and run it"
    curl localhost:7777/agents/coder/runs/<run_id>?session_id=demo

AgentOS, the queue and the database stay on this host; each turn runs Claude Code in a Modal
sandbox. With a queue, any replica may run the next attempt, so every replica must read the
same checkpoint directory.
"""

import os
from pathlib import Path

from agno.agents.claude import ClaudeAgent
from agno.db.postgres import PostgresDb
from agno.job_queue.config import QueueConfig, RedisCoordination
from agno.os import AgentOS
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.modal import ModalSandbox
from modal_image import runtime_image

db = PostgresDb(
    db_url=os.getenv(
        "AGNO_SANDBOX_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
    )
)
agent = ClaudeAgent(
    id="coder",
    model=os.getenv("AGNO_SANDBOX_MODEL", "claude-sonnet-4-6"),
    permission_mode="bypassPermissions",
    sandbox=ModalSandbox(
        runtime_image(),
        checkpoints=FileCheckpointStore(
            Path.home() / ".agno" / "sandbox" / "checkpoints"
        ),
    ),
)
agent_os = AgentOS(
    id="sandbox-claude-modal",
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
