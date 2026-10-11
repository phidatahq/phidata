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
    backend = os.environ.get("SANDBOX_PROVIDER", "docker")
    namespace = os.environ.get("SANDBOX_NAMESPACE", "agentos-sandbox-example")
    objects = FileCheckpointStore(Path(os.environ["SANDBOX_CHECKPOINT_DIRECTORY"]))
    if backend == "docker":
        provider = DockerSandboxProvider(namespace)
        transfer = DockerCheckpointTransfer(provider, objects)
    else:
        from agno.sandbox.allocation import PostgresAllocationJournal
        from agno.sandbox.hosted_transfer import HostedCheckpointTransfer

        journal = PostgresAllocationJournal(store)
        journal.setup()
        capacity = int(os.environ.get("SANDBOX_MAX_ALLOCATIONS", "10"))
        lifetime = int(os.environ.get("SANDBOX_LIFETIME", "1800"))
        if backend == "e2b":
            from agno.sandbox.e2b import E2BSandboxProvider

            provider = E2BSandboxProvider(
                namespace, journal, max_allocations=capacity, lifetime=lifetime
            )
        elif backend == "daytona":
            from agno.sandbox.daytona import DaytonaSandboxProvider

            provider = DaytonaSandboxProvider(
                namespace, journal, max_allocations=capacity, lifetime=lifetime
            )
        elif backend == "modal":
            from agno.sandbox.modal import ModalSandboxProvider

            provider = ModalSandboxProvider(
                namespace,
                journal,
                app_name=os.environ["AGNO_MODAL_APP"],
                max_allocations=capacity,
                lifetime=lifetime,
            )
        elif backend == "vercel":
            from agno.sandbox.vercel import VercelSandboxProvider

            provider = VercelSandboxProvider(
                namespace, journal, max_allocations=capacity, lifetime=lifetime
            )
        else:
            raise ValueError(
                "SANDBOX_PROVIDER must be docker, e2b, daytona, modal or vercel"
            )
        transfer = HostedCheckpointTransfer(provider, objects)
    harness = os.environ.get("SANDBOX_HARNESS", "claude")
    if harness not in ("claude", "codex", "fixture"):
        raise ValueError("SANDBOX_HARNESS must be claude, codex or fixture")
    # Explicitly forward only model credentials. Service Postgres/Redis settings
    # remain outside compute. Configure remote MCP credentials in runtime_config.
    if harness == "fixture":
        runtime_env = {"AGNO_SANDBOX_TEST_RUNTIME": "1"}
    else:
        credential = "ANTHROPIC_API_KEY" if harness == "claude" else "OPENAI_API_KEY"
        runtime_env = (
            {credential: os.environ[credential]} if credential in os.environ else {}
        )
    agent = SandboxAgent(
        id="coder",
        coordinator=SandboxCoordinator(store, provider, transfer),
        image=os.environ["SANDBOX_RUNTIME_IMAGE"],
        harness=cast(Literal["claude", "codex", "fixture"], harness),
        env=runtime_env,
        network="none"
        if harness == "fixture"
        else ("bridge" if backend == "docker" else "internet"),
        cpus=float(os.environ.get("SANDBOX_CPUS", "2")),
        memory_mb=int(
            os.environ.get(
                "SANDBOX_MEMORY_MB", "4096" if backend == "vercel" else "2048"
            )
        ),
        pids_limit=256 if backend == "docker" else None,
        workspace_mb=512 if backend == "docker" else None,
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
                key_prefix=namespace,
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
