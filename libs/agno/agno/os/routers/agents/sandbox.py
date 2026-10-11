"""Durable submission for sandbox agents in every HTTP response mode."""

import asyncio
import json
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from agno.db.schemas.jobs import QueuedJob
from agno.os.job_queue import aprepare_accepted_or_abort, normalize_idempotency_key


async def enqueue_sandbox_run(
    agent: Any,
    worker: Any,
    *,
    input: str,
    session_id: str,
    user_id: Optional[str],
    kwargs: Dict[str, Any],
    run_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    if (
        worker is None
        or worker.config.durable is not True
        or worker.config.redis is None
        or getattr(worker.store, "serializes_sessions", False) is not True
    ):
        raise ValueError(
            "Sandbox API execution requires a durable queue with Redis coordination and shared session admission"
        )
    if worker.resolve_component("agent", agent.get_id()) is not agent:
        raise ValueError("Sandbox submissions must use the registered agent instance")
    options = agent._submission(input, kwargs)
    await agent.coordinator.store._acheck_acceptance(agent.get_id(), session_id, user_id)
    payload = {"input": input, "kwargs": options, "stream": True, "serialize_session": True}
    if len(json.dumps(payload, allow_nan=False).encode()) > 1024 * 1024:
        raise ValueError("Sandbox submission exceeds 1 MiB")
    job = QueuedJob(
        id=run_id or str(uuid4()),
        component_type="agent",
        component_id=agent.get_id(),
        session_id=session_id,
        user_id=user_id,
        payload=payload,
        max_attempts=worker.config.max_attempts,
        deployment_id=worker.config.deployment_id,
        idempotency_key=normalize_idempotency_key(idempotency_key),
    ).to_dict()
    accepted = await worker.store.enqueue_job(job, max_depth=worker.config.max_queue_depth)
    if accepted["reason"] == "queue_full":
        raise HTTPException(status_code=429, detail="Job queue is full")
    if accepted["reason"] == "duplicate":
        existing = accepted.get("job")
        if existing is None or any(
            existing.get(key) != job.get(key) for key in ("component_type", "component_id", "user_id", "session_id")
        ):
            raise HTTPException(status_code=409, detail="Idempotency-Key belongs to a different submission scope")
        stored_payload = dict(existing.get("payload") or {})
        # Assigned by the queue at acceptance, never part of the user's request.
        stored_payload.pop("session_seq", None)
        if stored_payload != payload:
            raise HTTPException(status_code=409, detail="Idempotency-Key already has different input or options")
        return existing
    await aprepare_accepted_or_abort(worker, agent, "agent", job["id"], session_id, user_id, input, run_kwargs=options)
    # The queue row is authoritative even if registering the live stream fails.
    from agno.os.event_streams import get_event_stream
    from agno.run.base import RunStatus

    try:
        await get_event_stream().register_run(job["id"], RunStatus.pending)
    except Exception:
        pass
    return job


async def sandbox_run_response(
    agent: Any,
    worker: Any,
    request: Request,
    *,
    input: str,
    session_id: str,
    user_id: Optional[str],
    kwargs: Dict[str, Any],
    stream: bool,
    background: bool,
    version: Any = None,
) -> Any:
    if version is not None:
        raise HTTPException(
            status_code=400,
            detail="Sandbox runs require the registered agent version",
        )
    try:
        job = await enqueue_sandbox_run(
            agent,
            worker,
            input=input,
            session_id=session_id,
            user_id=user_id,
            kwargs=kwargs,
            idempotency_key=request.headers.get("idempotency-key"),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if stream:
        # Existing resume machinery chooses retained events or database replay,
        # including for an idempotent submission whose live keys have expired.
        from agno.os.routers.agents.router import _resume_stream_generator
        from agno.os.utils import queued_run_tail_streamer

        if job.get("status") in ("completed", "failed", "cancelled"):
            iterator = _resume_stream_generator(agent, job["id"], None, job["session_id"], user_id)
        else:
            iterator = queued_run_tail_streamer(job["id"])
        return StreamingResponse(iterator, media_type="text/event-stream")
    if background:
        from agno.os.job_queue import ticket_status_to_api

        return JSONResponse(
            status_code=202,
            content={
                "run_id": job["id"],
                "session_id": job["session_id"],
                "status": ticket_status_to_api(job["status"]) or "PENDING",
            },
        )
    while True:
        current = await worker.store.get_job(job["id"])
        if current is None:
            raise HTTPException(
                status_code=503, detail="Accepted sandbox job is temporarily unavailable; reconnect using its run ID"
            )
        if current["status"] in ("completed", "failed", "cancelled"):
            result = await agent.aget_run_output(job["id"], job["session_id"], user_id=user_id)
            if result is None:
                raise HTTPException(
                    status_code=503, detail="Sandbox result is temporarily unavailable; reconnect using its run ID"
                )
            return JSONResponse(content=result.to_dict())
        if await request.is_disconnected():
            return JSONResponse(
                status_code=202, content={"run_id": job["id"], "session_id": job["session_id"], "status": "RUNNING"}
            )
        await asyncio.sleep(0.1)
