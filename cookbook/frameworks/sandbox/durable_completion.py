"""Exercise atomic publication with real Postgres and credential-free fixture output.

Set AGNO_TEST_SANDBOX_DB_URL to a dedicated local Postgres database. This example
creates unique test tables, proves a staged result is not completion, and removes
its tables afterwards. It does not invoke a coding model or provision compute.
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
from uuid import uuid4

from agno.db.postgres import PostgresDb
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from agno.sandbox.base import SandboxHandle
from agno.sandbox.checkpoint import CheckpointArchive, FileCheckpointStore
from agno.sandbox.postgres import PostgresSandboxStore
from agno.session.agent import AgentSession

suffix = uuid4().hex[:12]
db = PostgresDb(
    db_url=os.environ["AGNO_TEST_SANDBOX_DB_URL"],
    session_table="sandbox_example_sessions_" + suffix,
    runs_table="sandbox_example_runs_" + suffix,
)
store = PostgresSandboxStore(db, table_name="sandbox_example_bindings_" + suffix)
store.setup()
try:
    session = AgentSession(
        session_id="example", agent_id="coder", user_id="user", created_at=int(time())
    )
    run = RunOutput(
        run_id="turn",
        session_id="example",
        agent_id="coder",
        user_id="user",
        status=RunStatus.running,
    )
    db.upsert_session(session)
    db.upsert_run(run=run, session_id=session.session_id, user_id="user")
    state = store.claim(
        agent_id="coder",
        session_id="example",
        user_id="user",
        run_id="turn",
        owner=uuid4().hex,
    )
    # Fixture handle only: an actual coordinator binds a provider-confirmed computer.
    handle = SandboxHandle(
        "fixture",
        "fixture",
        "coder",
        "example",
        state.record["generation"],
        "running",
        "fixture",
    )
    store.set_computer(state.lease, handle)
    run.status = RunStatus.completed
    run.content = "fixture result"
    store.stage_result(
        state.lease,
        {"run": run.to_dict(), "session": session.to_dict(include_runs=False)},
    )
    assert db.get_run("turn").status == RunStatus.running
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "workspace").mkdir()
        (root / "native").mkdir()
        (root / "workspace/result.txt").write_text("fixture result")
        CheckpointArchive().capture(
            {"workspace": root / "workspace", "native": root / "native"},
            root / "snapshot.tar",
            state={"run_id": "turn", "incarnation": state.record["incarnation"]},
        )
        reference = FileCheckpointStore(root / "objects").put(root / "snapshot.tar")
        store.stage_checkpoint(state.lease, reference)
        # Production callers must confirm provider shutdown first.
        store.confirm_stopped(state.lease, "fixture")
        committed = store.commit(state.lease)
        assert committed["status"] == "COMPLETED"
        recovered = db.get_session("example")
        assert (
            recovered.session_data["sandbox"]["checkpoint"]["sha256"]
            == reference.sha256
        )
        print(
            "Conversation and recovery reference committed together after checkpoint staging and confirmed cleanup."
        )
finally:
    with db.db_engine.begin() as connection:
        for table in (store.bindings, store.runs, store.sessions):
            table.drop(connection)
    db.db_engine.dispose()
