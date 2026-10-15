"""Run Product Engineer in a checkout pinned by the caller; no host workspace is mounted."""

from os import environ

from agno.agents.codex import CodexAgent
from agno.db.postgres import PostgresDb
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandbox

engineer = CodexAgent(
    id="product-engineer",
    name="Product Engineer",
    db=PostgresDb(db_url=environ["SANDBOX_DATABASE_URL"]),
    sandbox=DockerSandbox(
        image=environ["SANDBOX_IMAGE"],
        network="isolated",
        workspace_mb=1024,
        checkpoints=FileCheckpointStore(environ["SANDBOX_CHECKPOINTS"]),
    ),
    sandbox_mode="workspace-write",
    instructions="Inspect the requested repository, run checks, and report actual results. Do not merge or deploy.",
)

if __name__ == "__main__":
    result = engineer.run(
        "Inspect this application and report what would be required to upgrade AgentOS.",
        repository={
            "url": environ["REPOSITORY_URL"],
            "commit": environ["REPOSITORY_COMMIT"],
        },
        session_id=environ["ENGINEER_SESSION_ID"],
    )
    print(result.content)
