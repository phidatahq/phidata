"""Serialize sandboxed Task admission across deployment replicas before dispatch."""

import asyncio
import hashlib
from contextlib import asynccontextmanager
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text

from agno.company.execution import _call, _task_run_database
from agno.company.sandbox import _task_response
from agno.db.base import AsyncBaseDb


@asynccontextmanager
async def _admission_lock(db: Any, key: int):
    # A transaction-scoped advisory lock has no expiring lease: a slow submitter
    # cannot overlap a successor, and a disconnected submitter releases the lock.
    statement = text("SELECT pg_try_advisory_xact_lock(:key)")
    engine = db.db_engine
    if isinstance(db, AsyncBaseDb):
        async with engine.begin() as connection:
            if not (await connection.execute(statement, {"key": key})).scalar():
                raise HTTPException(409, "Another sandboxed Task start is being admitted")
            yield
    else:
        connection = await asyncio.to_thread(db.db_engine.connect)
        try:
            acquired = await asyncio.to_thread(lambda: connection.execute(statement, {"key": key}).scalar())
            if not acquired:
                raise HTTPException(409, "Another sandboxed Task start is being admitted")
            yield
        finally:
            await asyncio.shield(asyncio.to_thread(connection.close))


@asynccontextmanager
async def _sandbox_start_gate(os: Any, task: dict, queue: Any):
    candidates = (os._company_db, os.db, queue.config.db)
    db = next(
        (
            candidate
            for candidate in candidates
            if getattr(getattr(getattr(candidate, "db_engine", None), "dialect", None), "name", None) == "postgresql"
        ),
        None,
    )
    if db is None:
        raise HTTPException(503, "Sandboxed Company starts require a shared PostgreSQL database")
    namespace = ":".join(
        [
            "company-sandbox-start",
            db.db_schema,
            os._company_db.tasks_table_name,
            queue.config.deployment_id or "default",
        ]
    )
    key = int.from_bytes(hashlib.sha256(namespace.encode()).digest()[:8], "big", signed=True)
    async with _admission_lock(db, key):
        page = 1
        while True:
            rows, total = await _call(
                os._company_db, "get_tasks", status="in_progress", include_deleted=True, limit=100, page=page
            )
            for other in rows:
                if other["id"] == task["id"] or not other.get("job_id"):
                    continue
                if not _task_response(other, os.registry)["sandboxed"]:
                    continue
                job = await queue.store.get_job(other["job_id"])
                if job is not None and job.get("deployment_id") != queue.config.deployment_id:
                    continue
                live = job is not None and job["status"] not in {"completed", "failed", "cancelled"}
                if job is None:
                    run_db = _task_run_database(os, other)
                    run = await _call(run_db, "get_run", other["job_id"], deserialize=False)
                    live = run is not None and run["status"] not in {"COMPLETED", "ERROR", "CANCELLED"}
                if live:
                    raise HTTPException(409, "Another sandboxed Task is In progress with a live job")
            if page * 100 >= total:
                break
            page += 1
        yield
