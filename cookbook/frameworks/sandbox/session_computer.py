"""Two durable turns on replacement computers, with no model credentials.

Build the cookbook runtime image first. Set AGNO_TEST_RUNTIME_IMAGE and
AGNO_TEST_SANDBOX_DB_URL to dedicated local test resources. The example removes
its unique tables and temporary checkpoint directory when it finishes.
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from agno.db.postgres import PostgresDb
from agno.run.base import RunStatus
from agno.sandbox import SandboxHandle
from agno.sandbox.checkpoint import CheckpointRef, FileCheckpointStore
from agno.sandbox.coordinator import SandboxCoordinator
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.transfer import DockerCheckpointTransfer
from sqlalchemy import select

suffix = uuid4().hex[:12]
db = PostgresDb(
    db_url=os.environ["AGNO_TEST_SANDBOX_DB_URL"],
    session_table="computer_sessions_" + suffix,
    runs_table="computer_runs_" + suffix,
    sandbox_table="computer_bindings_" + suffix,
)
provider = DockerSandbox(
    os.environ["AGNO_TEST_RUNTIME_IMAGE"],
    namespace="computer-example-" + suffix,
    memory_mb=512,
    workspace_mb=32,
)
turn = dict(agent_id="coder", sdk="fixture", env={"AGNO_SANDBOX_TEST_RUNTIME": "1"})
with TemporaryDirectory() as directory:
    root = Path(directory)
    transfer = DockerCheckpointTransfer(provider, FileCheckpointStore(root / "objects"))
    coordinator = SandboxCoordinator(db, provider, transfer)
    store = coordinator.store
    try:
        first = coordinator.run(
            "example", run_id="first", input="Create a file", **turn
        )
        second = coordinator.run(
            "example", run_id="second", input="Continue on another computer", **turn
        )
        assert first.status == second.status == RunStatus.completed
        with db.db_engine.connect() as connection:
            binding = connection.execute(select(store.bindings)).mappings().one()
        assert binding["record"]["computer"] is None
        reference = CheckpointRef(**binding["record"]["checkpoint"])
        transfer.store.restore(reference, root / "inspect")
        assert (
            root / "inspect/workspace/fixture-effects.txt"
        ).read_text().splitlines() == [
            "first",
            "second",
        ]
        print(
            "Two turns completed. Both conversation results and workspace effects survived physical computer replacement."
        )
    finally:
        if hasattr(store, "bindings"):
            with db.db_engine.connect() as connection:
                records = connection.execute(select(store.bindings)).mappings().all()
            for record in records:
                if record["record"].get("computer"):
                    provider.destroy(SandboxHandle(**record["record"]["computer"]))
            with db.db_engine.begin() as connection:
                for table in (store.bindings, store.runs, store.sessions):
                    table.drop(connection)
        db.db_engine.dispose()
