"""Postgres ownership and atomic publication of sandbox recovery boundaries.

The coordinator owns this store. No database credentials belong inside compute.
A staged execution result or uploaded object alone never completes a service run.
"""

from __future__ import annotations

import asyncio
import hashlib
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
from agno.utils.string import sanitize_postgres_strings

try:
    from sqlalchemy import BigInteger, Column, DateTime, MetaData, String, Table, func, select, text, update
    from sqlalchemy.dialects.postgresql import JSONB, insert
    from sqlalchemy.engine import Connection
except ImportError:
    raise ImportError("Sandbox coordination requires sqlalchemy and a PostgreSQL driver")

_T = TypeVar("_T")


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


@dataclass(frozen=True)
class SandboxState:
    lease: SandboxLease
    expires_at: datetime
    record: Dict[str, Any] = field(repr=False)


class PostgresSandboxStore:
    """Session leases and finalization on the same database as service run history.

    Call setup/asetup before accepting traffic. Async methods support both
    Postgres adapters; synchronous methods require PostgresDb. Compute cleanup is
    acknowledged only after the coordinator confirms it through the provider.
    This store cannot independently prove a remote machine has stopped.
    """

    def __init__(self, db: Union[PostgresDb, AsyncPostgresDb], *, table_name: str = "agno_sandbox_bindings") -> None:
        if not isinstance(db, (PostgresDb, AsyncPostgresDb)):
            raise TypeError("Sandbox coordination requires PostgresDb or AsyncPostgresDb")
        self.db = db
        self.namespace = db.db_schema + "." + db.session_table_name
        self.bindings = Table(
            table_name,
            MetaData(schema=db.db_schema),
            Column("namespace", String, primary_key=True),
            Column("session_id", String, primary_key=True),
            Column("agent_id", String, nullable=False),
            Column("user_id", String, nullable=True),
            Column("epoch", BigInteger, nullable=False),
            Column("owner", String, nullable=True),
            Column("run_id", String, nullable=True),
            Column("queue_attempt", BigInteger, nullable=True),
            Column("expires_at", DateTime(timezone=True), nullable=True),
            Column("record", JSONB, nullable=False),
        )
        self.sessions: Optional[Table] = None
        self.runs: Optional[Table] = None

    def _sync(self, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if isinstance(self.db, AsyncPostgresDb):
            raise TypeError("Use async sandbox store methods with AsyncPostgresDb")
        return _sync(function(*args, **kwargs))

    async def asetup(self) -> None:
        if isinstance(self.db, AsyncPostgresDb):
            self.sessions = await self.db._get_table("sessions", create_table_if_not_found=True)
            self.runs = await self.db._get_table("runs", create_table_if_not_found=True)
        else:
            self.sessions = await asyncio.to_thread(self.db._get_table, "sessions", create_table_if_not_found=True)
            self.runs = await asyncio.to_thread(self.db._get_table, "runs", create_table_if_not_found=True)
        if self.sessions is None or self.runs is None:
            raise SandboxError("Sandbox setup requires service session and run tables")

        def create(connection: Connection) -> None:
            key = int.from_bytes(hashlib.sha256(self.bindings.fullname.encode()).digest()[:8], "big", signed=True)
            connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
            self.bindings.create(connection, checkfirst=True)

        await self._transaction(create)

    def setup(self) -> None:
        self._sync(self.asetup)

    async def _transaction(self, operation: Callable[[Connection], _T]) -> _T:
        if self.sessions is None or self.runs is None:
            raise SandboxError("Call sandbox store setup before accepting runs")
        if isinstance(self.db, AsyncPostgresDb):
            async with self.db.db_engine.begin() as connection:
                return await connection.run_sync(operation)
        db = self.db

        def transact() -> _T:
            with db.db_engine.begin() as connection:
                return operation(connection)

        return await asyncio.to_thread(transact)

    @staticmethod
    def _json(value: Any) -> Any:
        value = sanitize_postgres_strings(json.loads(json.dumps(value, allow_nan=False)))
        if len(json.dumps(value).encode()) > 16 * 1024 * 1024:
            raise ValueError("Sandbox coordination metadata exceeds 16 MiB")
        return value

    def _key(self, session_id: str) -> Any:
        return (self.bindings.c.namespace == self.namespace) & (self.bindings.c.session_id == session_id)

    def _service_run(self, connection: Connection, lease: SandboxLease, *, lock: bool = True) -> Any:
        assert self.runs is not None and self.sessions is not None
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
        now = connection.execute(select(func.clock_timestamp())).scalar_one()
        if (
            row is None
            or (row["agent_id"], row["user_id"], row["run_id"], row["epoch"], row["owner"], row["queue_attempt"])
            != (lease.agent_id, lease.user_id, lease.run_id, lease.epoch, lease.owner, lease.queue_attempt)
            or row["expires_at"] is None
            or row["expires_at"] <= now
        ):
            raise SandboxLeaseLost("Sandbox session lease expired or was fenced by another owner")
        _, session = self._service_run(connection, lease)
        if (session["session_data"] or {}).get("_sandbox_incarnation") != row["record"].get("incarnation"):
            raise SandboxLeaseLost("Service session was replaced; reconcile its previous sandbox before reuse")
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

        def claim(connection: Connection) -> SandboxState:
            connection.execute(
                insert(self.bindings)
                .values(
                    namespace=self.namespace,
                    session_id=session_id,
                    agent_id=agent_id,
                    user_id=user_id,
                    epoch=0,
                    record={"phase": "idle", "generation": uuid4().int, "checkpoint": None, "incarnation": uuid4().hex},
                )
                .on_conflict_do_nothing()
            )
            row = (
                connection.execute(select(self.bindings).where(self._key(session_id)).with_for_update())
                .mappings()
                .one()
            )
            if row["agent_id"] != agent_id or row["user_id"] != user_id:
                raise SandboxLeaseLost("Sandbox session ownership is immutable")
            if prepared_run is not None:
                value = self._json(prepared_run)
                if (
                    value.get("agent_id"),
                    value.get("session_id"),
                    value.get("user_id"),
                    value.get("run_id"),
                    value.get("queue_attempt"),
                ) != (agent_id, session_id, user_id, run_id, queue_attempt):
                    raise ValueError("Prepared run does not match the requested lease")
                self._prepare_service_run(connection, value)
            candidate = SandboxLease(agent_id, session_id, user_id, run_id, row["epoch"], owner, queue_attempt)
            run, session = self._service_run(connection, candidate)
            session_data = dict(session["session_data"] or {})
            if row["epoch"] == 0:
                if session_data.get("_sandbox_incarnation") is not None:
                    raise SandboxLeaseLost("Sandbox registry was replaced; reconcile existing recovery state")
                assert self.runs is not None
                historical = connection.execute(
                    select(self.runs.c.run_id)
                    .where(
                        (self.runs.c.session_id == session_id)
                        & (self.runs.c.run_id != run_id)
                        & self.runs.c.status.in_(["COMPLETED", "ERROR", "CANCELLED"])
                    )
                    .limit(1)
                ).first()
                if historical is not None:
                    raise SandboxError(
                        "Existing conversation has no sandbox checkpoint; start a new session or migrate explicitly"
                    )
                session_data["_sandbox_incarnation"] = row["record"]["incarnation"]
                assert self.sessions is not None
                connection.execute(
                    update(self.sessions)
                    .where(self.sessions.c.session_id == session_id)
                    .values(session_data=session_data)
                )
            elif session_data.get("_sandbox_incarnation") != row["record"]["incarnation"]:
                raise SandboxLeaseLost("Service session was replaced; reconcile its previous sandbox before reuse")
            now = connection.execute(select(func.clock_timestamp())).scalar_one()
            record = dict(row["record"])
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
            now = connection.execute(select(func.clock_timestamp())).scalar_one()
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
            assert self.runs is not None and self.sessions is not None
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
            run = {**previous_run["run_data"], **result["run"]}
            run["queue_attempt"] = lease.queue_attempt
            run["metadata"] = {
                **(run.get("metadata") or {}),
                "sandbox": {
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
            record.update(
                phase="idle",
                checkpoint=record["staged_checkpoint"],
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

    async def abegin_stop(self, lease: SandboxLease, *, status: str, reason: str) -> SandboxState:
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
            record.update(phase="stopping", stop_status=status, stop_reason=reason)
            if record.get("computer") is None:
                record["computer_stopped"] = True
            return self._write_record(connection, lease, record)

        return await self._transaction(begin)

    def begin_stop(self, lease: SandboxLease, *, status: str, reason: str) -> SandboxState:
        return self._sync(self.abegin_stop, lease, status=status, reason=reason)

    async def afinish_stop(self, lease: SandboxLease) -> Dict[str, Any]:
        """Retain the previous recovery boundary after confirmed cleanup of a failed turn."""

        def finish(connection: Connection) -> Dict[str, Any]:
            assert self.runs is not None
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
                    "sandbox": {
                        "recovery_run_id": record.get("last_run_id"),
                        "workspace_rolled_back": True,
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
        assert self.sessions is not None and self.runs is not None
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
        lease = SandboxLease(
            value["agent_id"],
            value["session_id"],
            value.get("user_id"),
            value["run_id"],
            0,
            "prepare",
            value.get("queue_attempt"),
        )
        row, _ = self._service_run(connection, lease)
        if row["run_data"].get("input") != value.get("input"):
            raise SandboxError("Run identity already exists with different input")
        if row["run_index"] is None:
            index = connection.execute(
                select(func.coalesce(func.max(self.runs.c.run_index), -1) + 1).where(
                    self.runs.c.session_id == value["session_id"]
                )
            ).scalar_one()
            connection.execute(update(self.runs).where(self.runs.c.run_id == value["run_id"]).values(run_index=index))

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
