"""Postgres event stream: cross-replica background run events with no Redis.

Events are rows in a per-run table, so any replica can replay and live-tail a
run another replica is executing. This is the zero-extra-infrastructure answer
for multi-replica deployments: the durable queue already requires Postgres, and
this stream rides the same database.

Design notes:
- Postgres is TTL'd transport here, not the source of truth. Terminal state and
  final output live on the run row; replay after the TTL falls back to that.
- One row per run carries its status, the writer generation and the index
  counter. ``add_event`` assigns the index and checks the generation fence in
  one UPDATE, so two writers can never hand out the same index and a zombie
  attempt's event is refused.
- ``tail()`` polls: it reads rows past the last index it yielded, and when none
  arrive it re-checks the run status so a producer that died without a
  terminal write never hangs a tail. A terminal status ends the tail only once
  every row has been yielded; a continuation flips the status back and the
  tail keeps going, which is what a pause sentinel does in the Redis stream.
- Expired runs are swept opportunistically from ``add_event`` and
  ``register_run`` at most once per minute per process.

Latency is bounded by ``poll_seconds`` (default 0.25 s), which is visible next
to Redis pub/sub but far below the time a model takes between events. LISTEN
and NOTIFY can replace the sleep later without changing the contract.
"""

import asyncio
import contextlib
import time
from typing import Any, AsyncIterator, List, Optional, Tuple

from agno.os.event_streams.base import BaseEventStream
from agno.run.base import RunStatus
from agno.utils.log import log_debug, log_warning

_TERMINAL = (RunStatus.completed, RunStatus.error, RunStatus.cancelled, RunStatus.paused)
_TERMINAL_VALUES = tuple(status.value for status in _TERMINAL)
_SWEEP_INTERVAL_SECONDS = 60.0


class PostgresEventStream(BaseEventStream):
    """Event stream on the deployment's Postgres, readable from every replica.

    Args:
        db: A ``PostgresDb`` or ``AsyncPostgresDb``, or a SQLAlchemy Postgres URL. The
            stream keeps its own small sync engine, so it never competes with the
            session store's pool for a connection during a long tail.
        table_prefix: Prefix for the two tables, ``<prefix>_runs`` and ``<prefix>_events``.
        schema: Schema for the tables. Defaults to the db's schema, else ``ai``.
        ttl_seconds: How long a run's rows are kept after its last write.
        poll_seconds: How long a tail sleeps when no new row has arrived.
    """

    def __init__(
        self,
        db: Any,
        *,
        table_prefix: str = "agno_os_events",
        schema: Optional[str] = None,
        ttl_seconds: int = 1800,
        poll_seconds: float = 0.25,
    ) -> None:
        from sqlalchemy import create_engine

        url = db if isinstance(db, str) else getattr(db, "db_url", None)
        if not url:
            engine = getattr(db, "db_engine", None)
            url = str(engine.url) if engine is not None else None
        if not url:
            raise ValueError("PostgresEventStream needs a Postgres URL or a PostgresDb")
        # The session store may use asyncpg; this stream runs short sync statements in a thread.
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        self._engine = create_engine(url, pool_size=2, max_overflow=4, pool_pre_ping=True)
        self.schema = schema or getattr(db, "db_schema", None) or "ai"
        self.runs_table = f'"{self.schema}"."{table_prefix}_runs"'
        self.events_table = f'"{self.schema}"."{table_prefix}_events"'
        self.ttl_seconds = int(ttl_seconds)
        self.poll_seconds = float(poll_seconds)
        self._ready = False
        self._ready_lock = asyncio.Lock()
        self._last_sweep = 0.0
        self._fence_refusals_logged: set = set()

    # ------------------------------------------------------------------
    # SQL plumbing
    # ------------------------------------------------------------------

    def _execute(self, statement: str, **params: Any) -> List[Any]:
        from sqlalchemy import text

        with self._engine.begin() as connection:
            result = connection.execute(text(statement), params)
            return list(result.fetchall()) if result.returns_rows else []

    async def _run(self, statement: str, **params: Any) -> List[Any]:
        await self._ensure_tables()
        return await asyncio.to_thread(self._execute, statement, **params)

    async def _ensure_tables(self) -> None:
        if self._ready:
            return
        async with self._ready_lock:
            if self._ready:
                return
            await asyncio.to_thread(self._create_tables)
            self._ready = True

    def _create_tables(self) -> None:
        from sqlalchemy import text

        with self._engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"'))
            connection.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {self.runs_table} ("
                    "run_id TEXT PRIMARY KEY, status TEXT NOT NULL, generation BIGINT, "
                    "next_index BIGINT NOT NULL DEFAULT 0, updated_at DOUBLE PRECISION NOT NULL)"
                )
            )
            connection.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {self.events_table} ("
                    "run_id TEXT NOT NULL, event_index BIGINT NOT NULL, sse TEXT NOT NULL, "
                    "created_at DOUBLE PRECISION NOT NULL, PRIMARY KEY (run_id, event_index))"
                )
            )

    async def _sweep_if_due(self) -> None:
        now = time.time()
        if now - self._last_sweep < _SWEEP_INTERVAL_SECONDS:
            return
        self._last_sweep = now
        cutoff = now - self.ttl_seconds
        with contextlib.suppress(Exception):
            await self._run(
                f"DELETE FROM {self.events_table} WHERE run_id IN "
                f"(SELECT run_id FROM {self.runs_table} WHERE updated_at < :cutoff)",
                cutoff=cutoff,
            )
            await self._run(f"DELETE FROM {self.runs_table} WHERE updated_at < :cutoff", cutoff=cutoff)

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    async def register_run(self, run_id: str, status: RunStatus = RunStatus.pending) -> None:
        await self._run(
            f"INSERT INTO {self.runs_table} (run_id, status, updated_at) VALUES (:run_id, :status, :now) "
            "ON CONFLICT (run_id) DO NOTHING",
            run_id=run_id,
            status=status.value,
            now=time.time(),
        )
        await self._sweep_if_due()

    async def _fenced_status(self, run_id: str, status: RunStatus, generation: Optional[int]) -> bool:
        """Write the status unless the writer's generation is older than the recorded one.

        Equal passes, newer self-heals the record forward, None bypasses the fence. A run the
        stream does not know is created, so a status write after the TTL still lands.
        """
        now = time.time()
        if generation is None:
            rows = await self._run(
                f"INSERT INTO {self.runs_table} (run_id, status, updated_at) VALUES (:run_id, :status, :now) "
                "ON CONFLICT (run_id) DO UPDATE SET status = EXCLUDED.status, updated_at = EXCLUDED.updated_at "
                "RETURNING run_id",
                run_id=run_id,
                status=status.value,
                now=now,
            )
            return bool(rows)
        rows = await self._run(
            f"INSERT INTO {self.runs_table} (run_id, status, generation, updated_at) "
            "VALUES (:run_id, :status, :generation, :now) "
            "ON CONFLICT (run_id) DO UPDATE SET status = EXCLUDED.status, generation = EXCLUDED.generation, "
            f"updated_at = EXCLUDED.updated_at WHERE {self.runs_table}.generation IS NULL "
            f"OR {self.runs_table}.generation <= EXCLUDED.generation RETURNING run_id",
            run_id=run_id,
            status=status.value,
            generation=generation,
            now=now,
        )
        if not rows:
            log_warning(
                f"Event stream: refused write for run {run_id} from stale generation {generation} - zombie writer fenced out"
            )
        return bool(rows)

    async def set_run_status(self, run_id: str, status: RunStatus, generation: Optional[int] = None) -> None:
        await self._fenced_status(run_id, status, generation)

    async def get_run_status(self, run_id: str) -> Optional[RunStatus]:
        rows = await self._run(f"SELECT status FROM {self.runs_table} WHERE run_id = :run_id", run_id=run_id)
        if not rows:
            return None
        with contextlib.suppress(ValueError):
            return RunStatus(rows[0][0])
        return None

    async def complete_run(self, run_id: str, status: RunStatus, generation: Optional[int] = None) -> None:
        if status not in _TERMINAL:
            # Contract: this call marks the run terminal, whatever it was handed.
            status = RunStatus.completed
        await self._fenced_status(run_id, status, generation)

    async def reopen_run(self, run_id: str, include_error: bool = False, floor: Optional[int] = None) -> bool:
        reopenable = [RunStatus.paused.value, RunStatus.pending.value]
        if include_error:
            reopenable.append(RunStatus.error.value)
        seed = (floor + 1) if floor is not None else 0
        now = time.time()
        # One statement: insert a missing run as PENDING with the seeded counter, or flip a
        # reopenable status back to PENDING without ever regressing a live counter.
        rows = await self._run(
            f"INSERT INTO {self.runs_table} (run_id, status, next_index, updated_at) "
            "VALUES (:run_id, 'PENDING', :seed, :now) "
            "ON CONFLICT (run_id) DO UPDATE SET status = 'PENDING', "
            f"next_index = GREATEST({self.runs_table}.next_index, EXCLUDED.next_index), updated_at = EXCLUDED.updated_at "
            f"WHERE {self.runs_table}.status = ANY(:reopenable) RETURNING run_id",
            run_id=run_id,
            seed=seed,
            now=now,
            reopenable=reopenable,
        )
        return bool(rows)

    async def begin_attempt(self, run_id: str, generation: int) -> None:
        await self._run(
            f"INSERT INTO {self.runs_table} (run_id, status, generation, updated_at) "
            "VALUES (:run_id, 'PENDING', :generation, :now) "
            f"ON CONFLICT (run_id) DO UPDATE SET generation = GREATEST(COALESCE({self.runs_table}.generation, 0), "
            "EXCLUDED.generation), updated_at = EXCLUDED.updated_at",
            run_id=run_id,
            generation=generation,
            now=time.time(),
        )

    async def cleanup_run(self, run_id: str) -> None:
        await self._run(f"DELETE FROM {self.events_table} WHERE run_id = :run_id", run_id=run_id)
        await self._run(f"DELETE FROM {self.runs_table} WHERE run_id = :run_id", run_id=run_id)

    async def reset_run_events(self, run_id: str, generation: Optional[int] = None) -> None:
        if generation is not None:
            rows = await self._run(f"SELECT generation FROM {self.runs_table} WHERE run_id = :run_id", run_id=run_id)
            if rows and rows[0][0] is not None and rows[0][0] > generation:
                log_warning(
                    f"Event stream: refused reset for run {run_id} from stale generation {generation} - zombie writer fenced out"
                )
                return
        # Events go; the counter and registration stay, so indices remain monotonic across attempts.
        await self._run(f"DELETE FROM {self.events_table} WHERE run_id = :run_id", run_id=run_id)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _log_fence_refusal(self, run_id: str, generation: int) -> None:
        if run_id not in self._fence_refusals_logged:
            self._fence_refusals_logged.add(run_id)
            log_warning(
                f"Event stream: refused event for run {run_id} from stale generation "
                f"{generation} - zombie writer fenced out (further refusals logged at DEBUG)"
            )
        else:
            log_debug(f"Event stream: refused event for run {run_id} from stale generation {generation}")

    async def add_event(self, run_id: str, event: Any, generation: Optional[int] = None) -> int:
        from agno.os.utils import format_sse_event_with_index

        now = time.time()
        # Index assignment and the generation fence in one statement: the UPDATE only lands
        # when the writer is at least as new as the recorded generation, and a newer writer
        # self-heals the record forward. An unknown run is created, as after a TTL expiry.
        rows = await self._run(
            f"INSERT INTO {self.runs_table} (run_id, status, generation, next_index, updated_at) "
            "VALUES (:run_id, 'RUNNING', :generation, 1, :now) "
            f"ON CONFLICT (run_id) DO UPDATE SET next_index = {self.runs_table}.next_index + 1, "
            f"generation = COALESCE(GREATEST({self.runs_table}.generation, EXCLUDED.generation), EXCLUDED.generation), "
            "updated_at = EXCLUDED.updated_at "
            f"WHERE :generation IS NULL OR {self.runs_table}.generation IS NULL OR {self.runs_table}.generation <= :generation "
            "RETURNING next_index - 1",
            run_id=run_id,
            generation=generation,
            now=now,
        )
        if not rows:
            self._log_fence_refusal(run_id, generation if generation is not None else -1)
            return -1
        event_index = int(rows[0][0])
        with contextlib.suppress(Exception):
            event.event_index = event_index
        sse_data = format_sse_event_with_index(event, event_index=event_index, run_id=run_id)
        await self._run(
            f"INSERT INTO {self.events_table} (run_id, event_index, sse, created_at) "
            "VALUES (:run_id, :event_index, :sse, :now) ON CONFLICT DO NOTHING",
            run_id=run_id,
            event_index=event_index,
            sse=sse_data,
            now=now,
        )
        await self._sweep_if_due()
        return event_index

    async def _events_after(self, run_id: str, last_event_index: int, limit: int = 500) -> List[Tuple[int, str]]:
        rows = await self._run(
            f"SELECT event_index, sse FROM {self.events_table} WHERE run_id = :run_id AND event_index > :last "
            "ORDER BY event_index LIMIT :limit",
            run_id=run_id,
            last=last_event_index,
            limit=limit,
        )
        return [(int(index), sse) for index, sse in rows]

    async def replay(self, run_id: str, last_event_index: Optional[int] = None) -> List[Tuple[int, Any]]:
        return await self._events_after(run_id, -1 if last_event_index is None else last_event_index, limit=100_000)

    async def get_last_index(self, run_id: str) -> int:
        rows = await self._run(f"SELECT next_index FROM {self.runs_table} WHERE run_id = :run_id", run_id=run_id)
        return int(rows[0][0]) - 1 if rows else -1

    async def get_event_count(self, run_id: str) -> int:
        rows = await self._run(f"SELECT COUNT(*) FROM {self.events_table} WHERE run_id = :run_id", run_id=run_id)
        return int(rows[0][0]) if rows else 0

    # ------------------------------------------------------------------
    # Live tail
    # ------------------------------------------------------------------

    async def tail(self, run_id: str, last_event_index: Optional[int] = None) -> AsyncIterator[Tuple[int, str]]:
        """Read rows past the last yielded index, sleep when there are none, and end once the
        run is terminal with nothing left to read. The status is read after an empty read, so
        an event written between the two is picked up on the next pass, never lost."""
        last_yielded = -1 if last_event_index is None else last_event_index
        while True:
            batch = await self._events_after(run_id, last_yielded)
            for event_index, sse in batch:
                yield event_index, sse
                last_yielded = event_index
            if batch:
                continue
            status = await self.get_run_status(run_id)
            if status is None or status in _TERMINAL:
                # A row written after the empty read and before this status read would be
                # missed by returning now; one more read closes that window.
                for event_index, sse in await self._events_after(run_id, last_yielded):
                    yield event_index, sse
                    last_yielded = event_index
                return
            await asyncio.sleep(self.poll_seconds)

    async def aclose(self) -> None:
        await asyncio.to_thread(self._engine.dispose)
