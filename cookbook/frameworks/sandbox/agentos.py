"""Serve a durable sandbox coding agent. See README for the required infrastructure."""

import os
from pathlib import Path
from typing import Literal, cast

from agno.agents.sandbox import SandboxAgent
from agno.db.postgres import PostgresDb
from agno.job_queue.config import QueueConfig, RedisCoordination
from agno.os import AgentOS
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.coordinator import SandboxCoordinator
from agno.sandbox.docker import DockerSandboxProvider
from agno.sandbox.postgres import PostgresSandboxStore
from agno.sandbox.transfer import DockerCheckpointTransfer


def create_agent_os() -> AgentOS:
    db = PostgresDb(db_url=os.environ["SANDBOX_DATABASE_URL"])
    store = PostgresSandboxStore(db)
    store.setup()
    provider = DockerSandboxProvider("agentos-sandbox-example")
    transfer = DockerCheckpointTransfer(
        provider, FileCheckpointStore(Path(os.environ["SANDBOX_CHECKPOINT_DIRECTORY"]))
    )
    harness = os.environ.get("SANDBOX_HARNESS", "claude")
    if harness not in ("claude", "codex", "fixture"):
        raise ValueError("SANDBOX_HARNESS must be claude, codex or fixture")
    # Explicitly forward only model credentials. Service Postgres/Redis settings
    # remain outside compute. Configure remote MCP credentials in runtime_config.
    runtime_env = {
        key: os.environ[key]
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
        if key in os.environ
    }
    if harness == "fixture":
        runtime_env = {"AGNO_SANDBOX_TEST_RUNTIME": "1"}
    agent = SandboxAgent(
        id="coder",
        coordinator=SandboxCoordinator(store, provider, transfer),
        image=os.environ["SANDBOX_RUNTIME_IMAGE"],
        harness=cast(Literal["claude", "codex", "fixture"], harness),
        env=runtime_env,
        network="none" if harness == "fixture" else "bridge",
    )
    return AgentOS(
        id="sandbox-example",
        agents=[agent],
        db=db,
        queue=QueueConfig(
            durable=True,
            db=db,
            redis=RedisCoordination(
                url=os.environ["SANDBOX_REDIS_URL"],
                key_prefix="agentos-sandbox-example",
            ),
            max_attempts=2,
            max_concurrency=4,
        ),
        telemetry=False,
    )


if __name__ == "__main__":
    agent_os = create_agent_os()
    agent_os.serve(
        app=agent_os.get_app(),
        port=int(os.environ.get("SANDBOX_PORT", "7777")),
        reload=False,
    )
