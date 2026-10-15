"""Walk through the sandbox completion store against real Postgres.

The coordinator drives this store for you; this example calls it directly so each
step of a sandbox turn is visible, printing what Postgres holds after every step:

1. A turn finishes in the sandbox, but the run stays RUNNING until the workspace
   checkpoint is staged and the computer is confirmed stopped. Then one
   transaction marks the run COMPLETED and points the session at the checkpoint.
2. Editing the session mid-turn (what AgentOS PATCH /sessions does) leaves the
   turn's lease intact.
3. A coordinator that stops renewing its lease is fenced: a second coordinator
   takes the turn over and the first one's writes are refused.
4. Cancelling a turn keeps the previous turn's checkpoint as the recovery point.

There is no setup step: the store's table is created on first use, in the same
PostgresDb as the agent's sessions and runs. No model calls and no containers;
the sandbox computer is a fixture handle. The tables are unique to this run and
dropped at the end.

Run Postgres with ./cookbook/scripts/run_pgvector.sh, or point
AGNO_TEST_SANDBOX_DB_URL at another local database.
"""

import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from agno.db.postgres import PostgresDb
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from agno.sandbox.base import SandboxHandle
from agno.sandbox.checkpoint import (
    CheckpointArchive,
    CheckpointRef,
    FileCheckpointStore,
)
from agno.sandbox.postgres import SandboxLeaseLost, SandboxState, _SandboxStore
from agno.session.agent import AgentSession

DB_URL = os.getenv(
    "AGNO_TEST_SANDBOX_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
)
AGENT, SESSION, USER = "coder", "example", "user"

suffix = uuid4().hex[:8]
db = PostgresDb(
    db_url=DB_URL,
    session_table="sandbox_example_sessions_" + suffix,
    runs_table="sandbox_example_runs_" + suffix,
    sandbox_table="sandbox_example_bindings_" + suffix,
)
store = _SandboxStore(db)
objects = TemporaryDirectory()  # stands in for durable checkpoint storage


def show(step: str, state: SandboxState, run_id: str) -> None:
    session = db.get_session(SESSION)
    pointer = (
        ((session.session_data or {}).get("sandbox") or {}).get("checkpoint")
        if session
        else None
    )
    print(step)
    print(f"    run {run_id}: {db.get_run(run_id).status}")
    print(
        f"    lease: phase={state.record['phase']} epoch={state.lease.epoch} owner={state.lease.owner[:8]}"
    )
    print(f"    session checkpoint: {pointer['sha256'][:12] if pointer else 'none'}")


def start_run(run_id: str) -> RunOutput:
    run = RunOutput(
        run_id=run_id,
        session_id=SESSION,
        agent_id=AGENT,
        user_id=USER,
        status=RunStatus.running,
    )
    db.upsert_run(run=run, session_id=SESSION, user_id=USER)
    return run


def claim(run_id: str, owner: str, lease_seconds: float = 60) -> SandboxState:
    return store.claim(
        agent_id=AGENT,
        session_id=SESSION,
        user_id=USER,
        run_id=run_id,
        owner=owner,
        lease_seconds=lease_seconds,
    )


def computer(state: SandboxState) -> SandboxHandle:
    # Fixture handle: a real coordinator binds the computer its provider created.
    return SandboxHandle(
        "computer-" + str(state.record["generation"])[-6:],
        "fixture",
        AGENT,
        SESSION,
        state.record["generation"],
        "running",
        "fixture",
    )


def checkpoint(workspace_text: str) -> CheckpointRef:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "workspace").mkdir()
        (root / "native").mkdir()
        (root / "workspace" / "result.txt").write_text(workspace_text)
        CheckpointArchive().capture(
            {"workspace": root / "workspace", "native": root / "native"},
            root / "snapshot.tar",
            state={},
        )
        return FileCheckpointStore(Path(objects.name)).put(root / "snapshot.tar")


try:
    db.upsert_session(
        AgentSession(
            session_id=SESSION,
            agent_id=AGENT,
            user_id=USER,
            created_at=int(time.time()),
        )
    )

    print("\n--- Turn 1: completion waits for the checkpoint and cleanup ---")
    run = start_run("turn-1")
    state = claim("turn-1", owner=uuid4().hex)
    show("claimed: this coordinator now owns the session", state, "turn-1")
    handle = computer(state)
    state = store.set_computer(state.lease, handle)
    run.status, run.content = RunStatus.completed, "Wrote result.txt"
    state = store.stage_result(
        state.lease,
        {"run": run.to_dict(), "session": {"session_id": SESSION, "user_id": USER}},
    )
    show(
        "result staged: the sandbox finished, but the run is still RUNNING",
        state,
        "turn-1",
    )
    first = checkpoint("turn 1")
    state = store.stage_checkpoint(state.lease, first)
    state = store.confirm_stopped(state.lease, handle.provider_ref)
    show("checkpoint staged and computer confirmed stopped", state, "turn-1")
    store.commit(state.lease)
    print("committed: run and session checkpoint written in one transaction")
    print(f"    run turn-1: {db.get_run('turn-1').status}")
    print(
        f"    session checkpoint: {db.get_session(SESSION).session_data['sandbox']['checkpoint']['sha256'][:12]}"
    )

    print("\n--- Turn 2: a session edit mid-turn, then a coordinator that stalls ---")
    start_run("turn-2")
    stale = db.get_session(SESSION)
    stalled = claim("turn-2", owner=uuid4().hex, lease_seconds=1)
    stale.session_data = {
        **(stale.session_data or {}),
        "session_name": "renamed mid-turn",
    }
    db.upsert_session(stale)
    show(
        "session renamed while the turn runs: the lease still holds",
        store.get(stalled.lease),
        "turn-2",
    )
    time.sleep(1.5)
    takeover = claim("turn-2", owner=uuid4().hex)
    show(
        "first coordinator stopped renewing; a second one took over", takeover, "turn-2"
    )
    try:
        store.set_computer(stalled.lease, computer(stalled))
    except SandboxLeaseLost as error:
        print(f"    first coordinator's late write refused: {error}")

    print("\n--- Turn 2 cancelled: turn 1's checkpoint stays the recovery point ---")
    state = store.begin_stop(
        takeover.lease, status="CANCELLED", reason="Cancelled by the user"
    )
    show("stop intent recorded before touching compute", state, "turn-2")
    store.finish_stop(state.lease)
    print("stop finished")
    print(f"    run turn-2: {db.get_run('turn-2').status}")
    pointer = db.get_session(SESSION).session_data["sandbox"]["checkpoint"]
    print(
        f"    session checkpoint: {pointer['sha256'][:12]} (turn 1: {first.sha256[:12]})"
    )
finally:
    with db.db_engine.begin() as connection:
        for name in ("bindings", "runs", "sessions"):
            if hasattr(store, name):
                getattr(store, name).drop(connection, checkfirst=True)
    db.db_engine.dispose()
    objects.cleanup()
