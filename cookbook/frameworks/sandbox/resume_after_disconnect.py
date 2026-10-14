"""Lose the caller mid-turn and pick the turn up from another coordinator.

A turn runs inside its container, not inside the caller. When the caller goes away
(a dropped connection, a restarted server), the coordinator steps back and the
turn keeps running. Any coordinator that later asks for the same run id and input
reattaches to that execution and gets its result; the work is not started again.

Uses the credential-free fixture runtime. Its turn here takes six seconds, and the
caller disconnects after three.

Prerequisites:
    ./cookbook/scripts/run_pgvector.sh
    python cookbook/frameworks/sandbox/build_image.py
"""

import asyncio
import os
import time
from contextlib import suppress
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
    namespace="resume-after-disconnect",
    memory_mb=512,
)
session_id = "resume-" + uuid4().hex[:8]
turn = dict(
    agent_id="coder",
    sdk="fixture",
    env={"AGNO_SANDBOX_TEST_RUNTIME": "1"},
    run_id=session_id + "-1",
    input="Refactor the module",
    config={"delay": 6, "steps": 6},
)


async def main() -> None:
    with TemporaryDirectory() as checkpoints:
        transfer = DockerCheckpointTransfer(
            sandbox, FileCheckpointStore(Path(checkpoints))
        )

        caller = asyncio.create_task(
            SandboxCoordinator(db, sandbox, transfer).arun(session_id, **turn)
        )
        await asyncio.sleep(3)
        caller.cancel()
        with suppress(asyncio.CancelledError):
            await caller
        print("Caller disconnected after 3s; the turn keeps running in its container")

        # Another coordinator, for example on another replica, asks for the same run.
        started = time.monotonic()
        result = await SandboxCoordinator(db, sandbox, transfer).arun(
            session_id, **turn
        )
        print(
            f"Another coordinator reattached: {result.status} - {result.content} "
            f"after {time.monotonic() - started:.1f}s, not a fresh 6s run"
        )


if __name__ == "__main__":
    asyncio.run(main())
