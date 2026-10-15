"""Postgres ownership and atomic publication of sandbox recovery boundaries.

The coordinator owns this store. No database credentials belong inside compute.
A staged execution result or uploaded object alone never completes a service run.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar, Union
from uuid import uuid4

from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.exceptions import SessionBusyError
from agno.sandbox.base import SandboxError, SandboxHandle, _sync
from agno.sandbox.checkpoint import CheckpointRef
from agno.sandbox.protocol import NATIVE_SESSION_KEYS
from agno.utils.string import sanitize_postgres_strings

try:
    from sqlalchemy import Table, func, select, update
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.engine import Connection
    from sqlalchemy.exc import IntegrityError
except ImportError:
    raise ImportError("Sandbox coordination requires sqlalchemy and a PostgreSQL driver")

_T = TypeVar("_T")

# Fields the runtime produces; service-owned identity, input and lineage stay as stored.
_RUNTIME_RUN_FIELDS = frozenset(
    (
        "content",
        "content_type",
        "reasoning_content",
        "reasoning_steps",
        "reasoning_messages",
        "model",
        "model_provider",
        "model_provider_data",
        "messages",
        "metrics",
        "compaction",
        "tools",
        "images",
        "videos",
        "audio",
        "files",
        "response_audio",
        "citations",
        "references",
        "followups",
        "events",
        "status",
        "last_checkpoint_at_message_index",
    )
)


class SandboxLeaseLost(SandboxError):
    """The caller no longer owns this session or queue attempt."""


class SandboxSessionBusy(SessionBusyError, SandboxError):
    def __init__(self, run_id: str) -> None:
        super().__init__("A sandbox session already has an active run; wait or reconcile that run", run_id=run_id)


class SandboxRunFinished(SandboxError):
    def __init__(self, run: Dict[str, Any]) -> None:
        self.run = run
        super().__init__("This service run is already terminal; return its persisted result")


@dataclass(frozen=True)
class SandboxLease:
    agent_id: str
    session_id: str
    user_id: Optional[str]
    run_id: str
    epoch: int
    owner: str = field(repr=False)
    queue_attempt: Optional[int] = None
    # Unique per binding row, so a lease for a deleted session never matches its recreation
    incarnation: Optional[str] = field(default=None, repr=False)


@dataclass(frozen=True)
class SandboxState:
    lease: SandboxLease
    expires_at: datetime
    record: Dict[str, Any] = field(repr=False)


class _SandboxStore:
    """Session leases and finalization on the same database as service run history.

    Tables live in the agent's PostgresDb (``sandbox_table`` names the lease
    table) and are created on first use. Async methods support both Postgres
    adapters; synchronous methods require PostgresDb. Compute cleanup is
    acknowledged only after the coordinator confirms it through the provider.
    This store cannot independently prove a remote machine has stopped.
    """

    sessions: Table
    runs: Table
    bindings: Table

    def __init__(self, db: Union[PostgresDb, AsyncPostgresDb]) -> None:
        if not isinstance(db, (PostgresDb, AsyncPostgresDb)):
            raise TypeError("Sandbox coordination requires PostgresDb or AsyncPostgresDb")
        self.db = db
        self.namespace = db.db_schema + "." + db.session_table_name
        self._tables_ready = False

    def _sync(self, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if isinstance(self.db, AsyncPostgresDb):
            raise TypeError("Use async sandbox store methods with AsyncPostgresDb")
        return _sync(function(*args, **kwargs))

    async def _table(self, table_type: str, table_name: str) -> Table:
        db = self.db
        try:
            if isinstance(db, AsyncPostgresDb):
                table = await db._get_table(table_type, create_table_if_not_found=True)
            else:
                table = await asyncio.to_thread(db._get_table, table_type, create_table_if_not_found=True)
        except Exception as exc:
            # Another process may have won the first CREATE TABLE.
            cause = getattr(exc, "orig", exc)
            if getattr(cause, "sqlstate", getattr(cause, "pgcode", None)) not in ("42P07", "23505"):
                raise
            db._invalidate_table_cache(table_name)
            if isinstance(db, AsyncPostgresDb):
                table = await db._get_table(table_type)
            else:
                table = await asyncio.to_thread(db._get_table, table_type)
        if table is None:
            raise SandboxError(f"Sandbox coordination could not create the {table_type} table")
        return table

    async def _ensure_tables(self) -> None:
        if self._tables_ready:
            return
        # Creation is idempotent, so concurrent first calls need no lock.
        self.sessions = await self._table("sessions", self.db.session_table_name)
        self.runs = await self._table("runs", self.db.runs_table_name)
        self.bindings = await self._table("sandbox_bindings", self.db.sandbox_table_name)
        self._tables_ready = True

    async def _transaction(self, operation: Callable[[Connection], _T]) -> _T:
        await self._ensure_tables()
        if isinstance(self.db, AsyncPostgresDb):
            async with self.db.db_engine.begin() as connection:
                return await connection.run_sync(operation)
        db = self.db

        def transact() -> _T:
            with db.db_engine.begin() as connection:
                return operation(connection)

        # Cancelling to_thread leaves the thread running; wait so a cancelled call never commits later.
        task = asyncio.ensure_future(asyncio.to_thread(transact))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await asyncio.wait([task])
            raise

    @staticmethod
    def _json(value: Any) -> Any:
        value = sanitize_postgres_strings(json.loads(json.dumps(value, allow_nan=False)))
        if len(json.dumps(value).encode()) > 16 * 1024 * 1024:
            raise ValueError("Sandbox coordination metadata exceeds 16 MiB")
        return value

    def _key(self, session_id: str) -> Any:
        return (self.bindings.c.namespace == self.namespace) & (self.bindings.c.session_id == session_id)

    def _service_run(self, connection: Connection, lease: SandboxLease, *, lock: bool = True) -> Any:
        query = select(self.runs).where(self.runs.c.run_id == lease.run_id)
        row = connection.execute(query.with_for_update() if lock else query).mappings().one_or_none()
        if (
            row is None
            or row["session_id"] != lease.session_id
            or row["agent_id"] != lease.agent_id
            or row["user_id"] != lease.user_id
        ):
            raise SandboxLeaseLost("Service run ownership does not match the sandbox lease")
        if row["run_data"].get("queue_attempt") != lease.queue_attempt:
            raise SandboxLeaseLost("A different queue attempt owns this service run")
        # Keep the core adapter's run -> session lock order.
        query = select(self.sessions).where(self.sessions.c.session_id == lease.session_id)
        session = connection.execute(query.with_for_update() if lock else query).mappings().one_or_none()
        if session is None or session["agent_id"] != lease.agent_id or session["user_id"] != lease.user_id:
            raise SandboxLeaseLost("Service session ownership does not match the sandbox lease")
        return row, session

    def _locked(self, connection: Connection, lease: SandboxLease) -> Any:
        row = (
            connection.execute(select(self.bindings).where(self._key(lease.session_id)).with_for_update())
            .mappings()
            .one_or_none()
        )
        now: datetime = connection.execute(select(func.clock_timestamp())).scalar_one()
        if (
            row is None
            or (row["agent_id"], row["user_id"], row["run_id"], row["epoch"], row["owner"], row["queue_attempt"])
            != (lease.agent_id, lease.user_id, lease.run_id, lease.epoch, lease.owner, lease.queue_attempt)
            or row["record"].get("incarnation") != lease.incarnation
            or row["expires_at"] is None
            or row["expires_at"] <= now
        ):
            raise SandboxLeaseLost("Sandbox session lease expired or was fenced by another owner")
        self._service_run(connection, lease)
        return row

    def _state(self, row: Any) -> SandboxState:
        return SandboxState(
            SandboxLease(
                row["agent_id"],
                row["session_id"],
                row["user_id"],
                row["run_id"],
                row["epoch"],
                row["owner"],
                row["queue_attempt"],
                row["record"].get("incarnation"),
            ),
            row["expires_at"],
            self._json(row["record"]),
        )

    def _write_record(self, connection: Connection, lease: SandboxLease, record: Dict[str, Any]) -> SandboxState:
        row = (
            connection.execute(
                update(self.bindings)
                .where(self._key(lease.session_id))
                .values(record=self._json(record))
                .returning(self.bindings)
            )
            .mappings()
            .one()
        )
        return self._state(row)

    async def aclaim(
        self,
        *,
        agent_id: str,
        session_id: str,
        user_id: Optional[str],
        run_id: str,
        owner: str,
        queue_attempt: Optional[int] = None,
        lease_seconds: float = 60,
        prepared_run: Optional[Dict[str, Any]] = None,
    ) -> SandboxState:
        for value in (agent_id, session_id, run_id, owner, *(() if user_id is None else (user_id,))):
            if not isinstance(value, str) or not value or "\x00" in value or len(value) > 512:
                raise ValueError("Sandbox lease identities must be nonempty bounded strings")
        if queue_attempt is not None and (type(queue_attempt) is not int or queue_attempt < 1):
            raise ValueError("Queue attempt must be a positive integer")
        if not math.isfinite(lease_seconds) or not 0 < lease_seconds <= 3600:
            raise ValueError("Lease duration must be between 0 and 3600 seconds")

        prepared: Optional[Dict[str, Any]] = None
        if prepared_run is not None:
            prepared = self._json(prepared_run)
            if (
                prepared.get("agent_id"),
                prepared.get("session_id"),
                prepared.get("user_id"),
                prepared.get("run_id"),
                prepared.get("queue_attempt"),
            ) != (agent_id, session_id, user_id, run_id, queue_attempt):
                raise ValueError("Prepared run does not match the requested lease")

        def claim(connection: Connection) -> SandboxState:
            if prepared is not None:
                # The binding's foreign key needs the session row; inserting it locks no existing row,
                # so the binding is still locked before any run or session row.
                self._insert_session(connection, prepared)
            try:
                connection.execute(
                    insert(self.bindings)
                    .values(
                        namespace=self.namespace,
                        session_id=session_id,
                        agent_id=agent_id,
                        user_id=user_id,
                        epoch=0,
                        record={
                            "phase": "idle",
                            "generation": uuid4().int,
                            "checkpoint": None,
                            "incarnation": uuid4().hex,
                        },
                    )
                    .on_conflict_do_nothing()
                )
            except IntegrityError as error:
                # The binding's foreign key: the service session does not exist.
                raise SandboxLeaseLost("Service session ownership does not match the sandbox lease") from error
            row = (
                connection.execute(select(self.bindings).where(self._key(session_id)).with_for_update())
                .mappings()
                .one()
            )
            if row["agent_id"] != agent_id or row["user_id"] != user_id:
                raise SandboxLeaseLost("Sandbox session ownership is immutable")
            if prepared is not None:
                self._prepare_service_run(connection, prepared)
            candidate = SandboxLease(agent_id, session_id, user_id, run_id, row["epoch"], owner, queue_attempt)
            run, _ = self._service_run(connection, candidate)
            if row["epoch"] == 0:
                # A first binding on a session with finished runs has no checkpoint to continue from.
                historical = connection.execute(
                    select(self.runs.c.run_id)
                    .where(
                        (self.runs.c.session_id == session_id)
                        & (self.runs.c.run_id != run_id)
                        & self.runs.c.status.in_(["COMPLETED", "ERROR", "CANCELLED"])
                        & func.coalesce(
                            self.runs.c.run_data["metadata"]["sandbox"]["never_executed"].as_boolean(), False
                        ).is_(False)
                    )
                    .limit(1)
                ).first()
                if historical is not None:
                    raise SandboxError(
                        "Existing conversation has no sandbox checkpoint; start a new session or migrate explicitly"
                    )
            record = dict(row["record"])
            now: datetime = connection.execute(select(func.clock_timestamp())).scalar_one()
            active = record["phase"] != "idle"
            if not active and str(run["status"]).upper() in ("COMPLETED", "CANCELLED", "ERROR"):
                raise SandboxRunFinished(dict(run["run_data"]))
            if active and row["run_id"] != run_id:
                raise SandboxSessionBusy(row["run_id"])
            newer_attempt = (
                queue_attempt is not None and row["queue_attempt"] is not None and queue_attempt > row["queue_attempt"]
            )
            same_owner = row["owner"] == owner and row["queue_attempt"] == queue_attempt
            lease_alive = row["expires_at"] is not None and row["expires_at"] > now
            if active and lease_alive and not same_owner and not newer_attempt:
                raise SandboxSessionBusy(row["run_id"])
            epoch = row["epoch"] if active and same_owner and lease_alive else row["epoch"] + 1
            if not active:
                record.update(
                    phase="executing",
                    generation=record["generation"] + 1,
                    computer=None,
                    computer_stopped=False,
                    stopped_ref=None,
                    stop_status=None,
                    stop_reason=None,
                    stop_retryable=False,
                    execution_id=uuid4().hex,
                    result=None,
                    staged_checkpoint=None,
                    staged_identity=None,
                    request_hash=None,
                )
            if active and str(run["status"]).upper() in ("CANCELLED", "ERROR"):
                record.update(
                    phase="stopping", stop_status=str(run["status"]).upper(), stop_reason="Service run was terminated"
                )
                if record.get("computer") is None:
                    record["computer_stopped"] = True
            updated = (
                connection.execute(
                    update(self.bindings)
                    .where(self._key(session_id))
                    .values(
                        epoch=epoch,
                        owner=owner,
                        run_id=run_id,
                        queue_attempt=queue_attempt,
                        expires_at=now + timedelta(seconds=lease_seconds),
                        record=record,
                    )
                    .returning(self.bindings)
                )
                .mappings()
                .one()
            )
            return self._state(updated)

        return await self._transaction(claim)

    def claim(self, **kwargs: Any) -> SandboxState:
        return self._sync(self.aclaim, **kwargs)

    async def aget(self, lease: SandboxLease) -> SandboxState:
        return await self._transaction(lambda connection: self._state(self._locked(connection, lease)))

    def get(self, lease: SandboxLease) -> SandboxState:
        return self._sync(self.aget, lease)

    async def arenew(self, lease: SandboxLease, *, lease_seconds: float = 60) -> SandboxState:
        if not math.isfinite(lease_seconds) or not 0 < lease_seconds <= 3600:
            raise ValueError("Lease duration must be between 0 and 3600 seconds")

        def renew(connection: Connection) -> SandboxState:
            self._locked(connection, lease)
            now: datetime = connection.execute(select(func.clock_timestamp())).scalar_one()
            row = (
                connection.execute(
                    update(self.bindings)
                    .where(self._key(lease.session_id))
                    .values(expires_at=now + timedelta(seconds=lease_seconds))
                    .returning(self.bindings)
                )
                .mappings()
                .one()
            )
            return self._state(row)

        return await self._transaction(renew)

    def renew(self, lease: SandboxLease, *, lease_seconds: float = 60) -> SandboxState:
        return self._sync(self.arenew, lease, lease_seconds=lease_seconds)

    async def aset_computer(self, lease: SandboxLease, computer: SandboxHandle) -> SandboxState:
        def bind(connection: Connection) -> SandboxState:
            record = dict(self._locked(connection, lease)["record"])
            if record["phase"] != "executing" or (computer.agent_id, computer.session_id, computer.generation) != (
                lease.agent_id,
                lease.session_id,
                record["generation"],
            ):
                raise SandboxError("Computer does not match the active session generation")
            serialized = asdict(computer)
            if record.get("computer") is not None and record["computer"] != serialized:
                raise SandboxError("A different computer is already bound to this generation")
            record["computer"] = serialized
            return self._write_record(connection, lease, record)

        return await self._transaction(bind)

    def set_computer(self, lease: SandboxLease, computer: SandboxHandle) -> SandboxState:
        return self._sync(self.aset_computer, lease, computer)

    async def astage_result(self, lease: SandboxLease, result: Dict[str, Any]) -> SandboxState:
        result = self._json(result)
        run, session = result.get("run", {}), result.get("session", {})
        if (
            run.get("run_id"),
            run.get("session_id"),
            run.get("agent_id"),
            run.get("user_id"),
            session.get("session_id"),
            session.get("user_id"),
        ) != (lease.run_id, lease.session_id, lease.agent_id, lease.user_id, lease.session_id, lease.user_id):
            raise SandboxError("Execution result identity does not match its lease")
        if run.get("status") not in ("COMPLETED", "ERROR", "CANCELLED"):
            raise SandboxError("Runtime result must describe a terminal execution")

        def stage(connection: Connection) -> SandboxState:
            record = dict(self._locked(connection, lease)["record"])
            if record.get("result") is not None:
                if record["result"] != result:
                    raise SandboxError("An execution result is immutable once staged")
                return self._state(self._locked(connection, lease))
            if record["phase"] != "executing" or record.get("computer") is None:
                raise SandboxError("Execution must have a bound computer before staging its result")
            record.update(phase="finalizing", result=result)
            return self._write_record(connection, lease, record)

        return await self._transaction(stage)

    def stage_result(self, lease: SandboxLease, result: Dict[str, Any]) -> SandboxState:
        return self._sync(self.astage_result, lease, result)

    async def astage_checkpoint(self, lease: SandboxLease, checkpoint: CheckpointRef) -> SandboxState:
        def stage(connection: Connection) -> SandboxState:
            row = self._locked(connection, lease)
            record = dict(row["record"])
            if record["phase"] != "finalizing" or record.get("result") is None:
                raise SandboxError("Checkpoint staging requires a retained execution result")
            value = asdict(checkpoint)
            if record.get("staged_checkpoint") is not None and record["staged_checkpoint"] != value:
                raise SandboxError("A staged checkpoint is immutable; reconcile its acknowledgement")
            record["staged_checkpoint"] = value
            return self._write_record(connection, lease, record)

        return await self._transaction(stage)

    def stage_checkpoint(self, lease: SandboxLease, checkpoint: CheckpointRef) -> SandboxState:
        return self._sync(self.astage_checkpoint, lease, checkpoint)

    async def aconfirm_stopped(self, lease: SandboxLease, provider_ref: str) -> SandboxState:
        """Record provider-confirmed shutdown, never a caller's assumption after a timeout."""

        def stopped(connection: Connection) -> SandboxState:
            row = self._locked(connection, lease)
            record = dict(row["record"])
            computer = record.get("computer")
            if computer is None or computer["provider_ref"] != provider_ref:
                if record.get("stopped_ref") == provider_ref:
                    return self._state(row)
                raise SandboxError("Shutdown acknowledgement does not match the bound computer")
            if record["phase"] not in ("finalizing", "stopping"):
                raise SandboxError("Persist a shutdown intent before retiring compute")
            if record["phase"] == "finalizing" and record.get("staged_checkpoint") is None:
                raise SandboxError("Persist a recovery checkpoint before retiring finalized execution")
            record.update(computer=None, computer_stopped=True, stopped_ref=provider_ref)
            return self._write_record(connection, lease, record)

        return await self._transaction(stopped)

    def confirm_stopped(self, lease: SandboxLease, provider_ref: str) -> SandboxState:
        return self._sync(self.aconfirm_stopped, lease, provider_ref)

    async def acommit(self, lease: SandboxLease) -> Dict[str, Any]:
        def commit(connection: Connection) -> Dict[str, Any]:
            row = self._locked(connection, lease)
            record = dict(row["record"])
            if (
                record["phase"] != "finalizing"
                or not record.get("staged_checkpoint")
                or not record.get("computer_stopped")
            ):
                raise SandboxError("Durable completion requires staged recovery bytes and confirmed compute cleanup")
            previous_run, session = self._service_run(connection, lease)
            if str(previous_run["status"]).upper() in ("COMPLETED", "CANCELLED", "ERROR"):
                raise SandboxRunFinished(dict(previous_run["run_data"]))
            result = record["result"]
            run = dict(previous_run["run_data"])
            run.update({key: value for key, value in result["run"].items() if key in _RUNTIME_RUN_FIELDS})
            run["queue_attempt"] = lease.queue_attempt
            native_metadata = result["run"].get("metadata") or {}
            run["metadata"] = {
                **(previous_run["run_data"].get("metadata") or {}),
                **{
                    key: native_metadata[key]
                    for key in ("warnings", "attempts", "retryable", "error_type")
                    if key in native_metadata
                },
                "sandbox": {
                    "native_metadata": native_metadata,
                    "epoch": lease.epoch,
                    "generation": record["generation"],
                    "checkpoint": record["staged_checkpoint"],
                    "execution_id": record["execution_id"],
                },
            }
            session_data = dict(session["session_data"] or {})
            session_data["sandbox"] = {
                "native": result["session"].get("session_data") or {},
                "checkpoint": record["staged_checkpoint"],
                "run_id": lease.run_id,
                "epoch": lease.epoch,
            }
            connection.execute(
                update(self.runs)
                .where(self.runs.c.run_id == lease.run_id)
                .values(status=run["status"], run_data=self._json(run), updated_at=int(time.time()))
            )
            connection.execute(
                update(self.sessions)
                .where(self.sessions.c.session_id == lease.session_id)
                .values(session_data=self._json(session_data), updated_at=int(time.time()))
            )
            native = result["session"].get("session_data") or {}
            record.update(
                phase="idle",
                checkpoint=record["staged_checkpoint"],
                # Native conversation ids the checkpoint holds; the next turn requires exactly these.
                native={key: native[key] for key in NATIVE_SESSION_KEYS.values() if native.get(key)},
                checkpoint_identity=record.get("staged_identity"),
                last_run_id=lease.run_id,
                result=None,
                staged_checkpoint=None,
            )
            connection.execute(
                update(self.bindings)
                .where(self._key(lease.session_id))
                .values(owner=None, run_id=None, queue_attempt=None, expires_at=None, record=record)
            )
            return run

        return await self._transaction(commit)

    def commit(self, lease: SandboxLease) -> Dict[str, Any]:
        return self._sync(self.acommit, lease)

    async def abegin_stop(
        self, lease: SandboxLease, *, status: str, reason: str, retryable: bool = False
    ) -> SandboxState:
        """Fence cancellation/failure before destroying compute; takeover only reconciles it."""
        if status not in ("ERROR", "CANCELLED") or not isinstance(reason, str) or len(reason) > 8192:
            raise ValueError("Shutdown requires a bounded error or cancellation reason")

        def begin(connection: Connection) -> SandboxState:
            row = self._locked(connection, lease)
            record = dict(row["record"])
            if record["phase"] == "stopping":
                return self._state(row)
            if record["phase"] not in ("executing", "finalizing"):
                raise SandboxError("Only an active execution can be stopped")
            record.update(phase="stopping", stop_status=status, stop_reason=reason, stop_retryable=retryable)
            if record.get("computer") is None:
                record["computer_stopped"] = True
            return self._write_record(connection, lease, record)

        return await self._transaction(begin)

    def begin_stop(self, lease: SandboxLease, *, status: str, reason: str, retryable: bool = False) -> SandboxState:
        return self._sync(self.abegin_stop, lease, status=status, reason=reason, retryable=retryable)

    async def afinish_stop(self, lease: SandboxLease) -> Dict[str, Any]:
        """Retain the previous recovery boundary after confirmed cleanup of a failed turn."""

        def finish(connection: Connection) -> Dict[str, Any]:
            record = dict(self._locked(connection, lease)["record"])
            if record["phase"] != "stopping" or not record.get("computer_stopped"):
                raise SandboxError("Stop completion requires confirmed compute cleanup")
            previous_run, _ = self._service_run(connection, lease)
            run = dict(previous_run["run_data"])
            if str(previous_run["status"]).upper() == "COMPLETED":
                raise SandboxRunFinished(run)
            if str(previous_run["status"]).upper() not in ("ERROR", "CANCELLED"):
                runtime_run = (record.get("result") or {}).get("run", {})
                for key in ("tools", "messages", "metrics"):
                    if key in runtime_run:
                        run[key] = runtime_run[key]
                run.update(status=record["stop_status"], content=record["stop_reason"])
                run["metadata"] = {
                    **(run.get("metadata") or {}),
                    "retryable": record.get("stop_retryable", False),
                    "sandbox": {
                        "native_metadata": runtime_run.get("metadata") or {},
                        "recovery_run_id": record.get("last_run_id"),
                        "workspace_rolled_back": True,
                        "epoch": lease.epoch,
                        "execution_id": record["execution_id"],
                    },
                }
                connection.execute(
                    update(self.runs)
                    .where(self.runs.c.run_id == lease.run_id)
                    .values(status=run["status"], run_data=self._json(run), updated_at=int(time.time()))
                )
            record.update(phase="idle", result=None, staged_checkpoint=None)
            connection.execute(
                update(self.bindings)
                .where(self._key(lease.session_id))
                .values(owner=None, run_id=None, queue_attempt=None, expires_at=None, record=record)
            )
            return run

        return await self._transaction(finish)

    def finish_stop(self, lease: SandboxLease) -> Dict[str, Any]:
        return self._sync(self.afinish_stop, lease)

    def _prepare_service_run(self, connection: Connection, value: Dict[str, Any]) -> None:
        if value.get("status") not in ("PENDING", "RUNNING"):
            raise ValueError("A prepared sandbox run cannot be terminal")
        for key in ("run_id", "session_id", "agent_id"):
            if not isinstance(value.get(key), str) or not value[key] or len(value[key]) > 256:
                raise ValueError("Sandbox runs require bounded service identities")
        self._insert_session(connection, value)
        connection.execute(
            insert(self.runs)
            .values(
                run_id=value["run_id"],
                session_id=value["session_id"],
                agent_id=value["agent_id"],
                user_id=value.get("user_id"),
                run_type="agent",
                status=value["status"],
                run_data=value,
                created_at=value.get("created_at", int(time.time())),
            )
            .on_conflict_do_nothing()
        )
        attempt = value.get("queue_attempt")
        if value["status"] == "PENDING":
            # A worker may already have claimed the accepted run; keep its attempt.
            existing: Dict[str, Any] = connection.execute(
                select(self.runs.c.run_data).where(self.runs.c.run_id == value["run_id"]).with_for_update()
            ).scalar_one()
            attempt = existing.get("queue_attempt")
        lease = SandboxLease(
            value["agent_id"],
            value["session_id"],
            value.get("user_id"),
            value["run_id"],
            0,
            "prepare",
            attempt,
        )
        row, _ = self._service_run(connection, lease)
        if row["run_data"].get("input") != value.get("input"):
            raise SandboxError("Run identity already exists with different input")
        if row["run_index"] is None:
            index: int = connection.execute(
                select(func.coalesce(func.max(self.runs.c.run_index), -1) + 1).where(
                    self.runs.c.session_id == value["session_id"]
                )
            ).scalar_one()
            connection.execute(update(self.runs).where(self.runs.c.run_id == value["run_id"]).values(run_index=index))

    def _insert_session(self, connection: Connection, value: Dict[str, Any]) -> None:
        connection.execute(
            insert(self.sessions)
            .values(
                session_id=value["session_id"],
                agent_id=value["agent_id"],
                user_id=value.get("user_id"),
                session_type="agent",
                created_at=int(time.time()),
                session_data={},
            )
            .on_conflict_do_nothing()
        )

    async def _apublish_events(self, run: Dict[str, Any], events: list[Dict[str, Any]]) -> None:
        """Attach transport indices without rewriting a committed recovery boundary."""

        def publish(connection: Connection) -> None:
            row = (
                connection.execute(select(self.runs).where(self.runs.c.run_id == run["run_id"]).with_for_update())
                .mappings()
                .first()
            )
            if row is None:
                raise SandboxLeaseLost("Run disappeared before event retention")
            previous = dict(row["run_data"])
            identity = (run.get("metadata") or {}).get("sandbox") or {}
            stored_identity = (previous.get("metadata") or {}).get("sandbox") or {}
            if (
                any(
                    previous.get(key) != run.get(key)
                    for key in ("run_id", "session_id", "agent_id", "user_id", "queue_attempt", "status")
                )
                or not identity.get("execution_id")
                or any(stored_identity.get(key) != identity.get(key) for key in ("execution_id", "epoch"))
            ):
                raise SandboxLeaseLost("Event writer no longer owns this run result")
            retained = {
                event["event_index"]: event
                for event in previous.get("events", [])
                if event.get("event_index") is not None
            }
            retained.update({event["event_index"]: event for event in events if event.get("event_index") is not None})
            if retained:
                previous["events"] = [retained[key] for key in sorted(retained)]
                connection.execute(
                    update(self.runs).where(self.runs.c.run_id == run["run_id"]).values(run_data=self._json(previous))
                )

        await self._transaction(publish)

    async def _aclaim_stop(
        self,
        *,
        agent_id: str,
        session_id: str,
        user_id: Optional[str],
        run_id: str,
        queue_attempt: Optional[int],
        status: str,
        reason: str,
        cancellation_stage: Optional[str] = None,
    ) -> Any:
        """Fence execution before a queue terminal path retires its compute."""
        from agno.run.status_persist import RunPersistOutcome

        if status not in ("ERROR", "CANCELLED"):
            raise ValueError("Queue termination requires ERROR or CANCELLED")

        def stop(connection: Connection) -> Any:
            # Insert an idle binding to serialize even a never-started run with
            # its first coordinator. A plain SELECT cannot lock an absent row.
            try:
                with connection.begin_nested():
                    connection.execute(
                        insert(self.bindings)
                        .values(
                            namespace=self.namespace,
                            session_id=session_id,
                            agent_id=agent_id,
                            user_id=user_id,
                            epoch=0,
                            record={
                                "phase": "idle",
                                "generation": uuid4().int,
                                "checkpoint": None,
                                "incarnation": uuid4().hex,
                            },
                        )
                        .on_conflict_do_nothing()
                    )
            except IntegrityError:
                # The binding's foreign key: the session, and with it the run, was deleted.
                return RunPersistOutcome.MISSING
            binding = (
                connection.execute(select(self.bindings).where(self._key(session_id)).with_for_update())
                .mappings()
                .one()
            )
            # A session bound to another owner can never have executed this run.
            foreign = binding["agent_id"] != agent_id or binding["user_id"] != user_id
            row = (
                connection.execute(select(self.runs).where(self.runs.c.run_id == run_id).with_for_update())
                .mappings()
                .first()
            )
            if row is None or (row["session_id"], row["agent_id"], row["user_id"]) != (session_id, agent_id, user_id):
                return RunPersistOutcome.MISSING
            run = dict(row["run_data"])
            actual_attempt = run.get("queue_attempt")
            if actual_attempt != queue_attempt and not (actual_attempt is None and queue_attempt == 0):
                return RunPersistOutcome.STALE_ATTEMPT
            record = dict(binding["record"])
            active = not foreign and record["phase"] != "idle" and binding["run_id"] == run_id
            if not active:
                if str(row["status"]).upper() in ("COMPLETED", "CANCELLED"):
                    return RunPersistOutcome.TERMINAL_REFUSED
                run.update(status=status, content=run.get("content") or reason)
                run["metadata"] = {**(run.get("metadata") or {}), "retryable": False}
                if foreign or binding["epoch"] == 0:
                    run["metadata"]["sandbox"] = {"never_executed": True}
                if status == "CANCELLED" and cancellation_stage is not None:
                    run["cancellation_stage"] = cancellation_stage
                connection.execute(
                    update(self.runs)
                    .where(self.runs.c.run_id == run_id)
                    .values(status=status, run_data=self._json(run), updated_at=int(time.time()))
                )
                return RunPersistOutcome.UPDATED
            # Take over an interrupted stop without rewriting the status it already committed to.
            if record["phase"] != "stopping":
                record.update(phase="stopping", stop_status=status, stop_reason=reason, stop_retryable=False)
            if record.get("computer") is None:
                record["computer_stopped"] = True
            now: datetime = connection.execute(select(func.clock_timestamp())).scalar_one()
            updated = (
                connection.execute(
                    update(self.bindings)
                    .where(self._key(session_id))
                    .values(
                        epoch=binding["epoch"] + 1,
                        owner=uuid4().hex,
                        queue_attempt=actual_attempt,
                        expires_at=now + timedelta(seconds=600),
                        record=self._json(record),
                    )
                    .returning(self.bindings)
                )
                .mappings()
                .one()
            )
            return self._state(updated)

        return await self._transaction(stop)

    async def aprepare(self, run: Dict[str, Any]) -> None:
        """Insert an accepted queued run without rewriting existing session recovery metadata."""
        value = self._json(run)
        await self._transaction(lambda connection: self._prepare_service_run(connection, value))

    def prepare(self, run: Dict[str, Any]) -> None:
        self._sync(self.aprepare, run)

    async def _aoperation(
        self, lease: SandboxLease, operation: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> SandboxState:
        # Hold the ownership rows through a bounded provider mutation. A concurrent
        # takeover waits until it drains, then checks ownership against the DB clock.
        # This closes the check-then-act gap between a lease read and provider calls.
        async def perform() -> SandboxState:
            await self._ensure_tables()
            if isinstance(self.db, AsyncPostgresDb):
                async with self.db.db_engine.begin() as connection:
                    row = await connection.run_sync(lambda c: self._locked(c, lease))
                    record = await operation(self._json(row["record"]))
                    return await connection.run_sync(lambda c: self._write_record(c, lease, record))
            sync_connection = await asyncio.to_thread(self.db.db_engine.connect)
            sync_transaction = await asyncio.to_thread(sync_connection.begin)
            try:
                row = await asyncio.to_thread(self._locked, sync_connection, lease)
                record = await operation(self._json(row["record"]))
                state = await asyncio.to_thread(self._write_record, sync_connection, lease, record)
                await asyncio.to_thread(sync_transaction.commit)
                return state
            except BaseException:
                await asyncio.to_thread(sync_transaction.rollback)
                raise
            finally:
                await asyncio.to_thread(sync_connection.close)

        task = asyncio.create_task(perform())
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # Closing a transaction while its provider operation still runs would
            # let the next owner mutate that same computer concurrently.
            await task
            raise

    async def arelinquish(self, lease: SandboxLease) -> None:
        """Detach the coordinator after draining its control calls; preserve ongoing execution."""

        def release(connection: Connection) -> None:
            self._locked(connection, lease)
            connection.execute(
                update(self.bindings).where(self._key(lease.session_id)).values(expires_at=func.clock_timestamp())
            )

        await self._transaction(release)

    def relinquish(self, lease: SandboxLease) -> None:
        self._sync(self.arelinquish, lease)
