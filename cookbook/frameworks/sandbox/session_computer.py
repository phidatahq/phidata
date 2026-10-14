"""Run several turns of one session, each on a fresh computer.

For every turn the coordinator creates a container, restores the session's last
checkpoint into it, runs the turn, saves a new checkpoint, removes the container,
and only then marks the run completed. The next turn starts from that checkpoint
on a new container.

The fixture runtime stands in for Claude or Codex, so no model credentials are
needed. It keeps a native conversation id like theirs, and every turn after the
first must find the one the previous turn committed: turn 2 completing means the
restore brought the conversation back.

Prerequisites:
    ./cookbook/scripts/run_pgvector.sh
    python cookbook/frameworks/sandbox/build_image.py
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from agno.db.postgres import PostgresDb
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.coordinator import SandboxCoordinator
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.transfer import DockerCheckpointTransfer

db = PostgresDb(
    db_url=os.getenv(
        "AGNO_SANDBOX_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
    )
)
sandbox = DockerSandbox(
    os.getenv("AGNO_SANDBOX_IMAGE", "agno-sandbox:local"),
    namespace="session-computer",
    memory_mb=512,
)
session_id = "session-computer-" + uuid4().hex[:8]
turn = dict(agent_id="coder", sdk="fixture", env={"AGNO_SANDBOX_TEST_RUNTIME": "1"})

# Use storage every coordinator replica can reach; a temporary directory is for the example only.
with TemporaryDirectory() as checkpoints:
    transfer = DockerCheckpointTransfer(sandbox, FileCheckpointStore(Path(checkpoints)))
    coordinator = SandboxCoordinator(db, sandbox, transfer)

    first = coordinator.run(
        session_id, run_id=session_id + "-1", input="Write the first draft", **turn
    )
    print(f"Turn 1 on a fresh computer: {first.status} - {first.content}")

    second = coordinator.run(
        session_id, run_id=session_id + "-2", input="Revise the draft", **turn
    )
    print(f"Turn 2 on another fresh computer: {second.status} - {second.content}")

    # A retry of a finished run, say after a lost response, returns the stored result
    # instead of running the turn again.
    retry = coordinator.run(
        session_id, run_id=second.run_id, input="Revise the draft", **turn
    )
    print(f"Retrying turn 2: {retry.status} - {retry.content}")
