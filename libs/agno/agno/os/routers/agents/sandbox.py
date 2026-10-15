"""Durable submission for sandboxed agents in every HTTP response mode."""

import asyncio
import base64
import contextlib
import json
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from agno.db.schemas.jobs import QueuedJob
from agno.media import File, Image
from agno.os.job_queue import aprepare_accepted_or_abort, normalize_idempotency_key

_JSON_ATTACHMENT_KEYS = {
    "images": {"content", "format", "mime_type", "id"},
    "files": {"content", "filename", "name", "format", "mime_type", "id"},
}
_FORBIDDEN_SOURCES = ("filepath", "url", "media_reference", "external")


def _attachment(item: Any, kind: str, index: int) -> Any:
    """One uploaded object or JSON item as an Image/File holding inline bytes, or a ValueError naming it."""
    cls = Image if kind == "images" else File
    label = f"{kind[:-1]} {index + 1}"
    if isinstance(item, dict):
        unknown = sorted(set(item) - _JSON_ATTACHMENT_KEYS[kind])
        if unknown:
            raise ValueError(f"Unsupported field(s) on {label}: {', '.join(unknown)}")
        content = item.get("content")
        if not isinstance(content, str) or not content:
            raise ValueError(f"The {label} needs non-empty base64 content")
        try:
            data = base64.b64decode(content, validate=True)
        except ValueError as error:
            raise ValueError(f"The {label} content is not valid base64") from error
        fields: Dict[str, Any] = {"format": item.get("format"), "mime_type": item.get("mime_type")}
        if kind == "files":
            name, filename = item.get("name"), item.get("filename")
            if name is not None and filename is not None and name != filename:
                raise ValueError(f"The {label} gives different name and filename values")
            fields["filename"] = filename if filename is not None else name
        try:
            return cls(content=data, **fields)
        except Exception as error:
            raise ValueError(f"The {label} has an unsupported format, mime_type or filename") from error
    if not isinstance(item, cls):
        raise ValueError(f"The {label} must be an uploaded file or a JSON object")
    if any(getattr(item, source, None) for source in _FORBIDDEN_SOURCES):
        raise ValueError(f"The {label} may not name a service path or a remote reference")
    if getattr(item, "metadata", None):
        raise ValueError(f"The {label} has metadata, which sandbox attachments do not carry")
    if not isinstance(item.content, bytes) or not item.content:
        raise ValueError(f"The {label} is empty")
    return item


def sandbox_attachments(
    *,
    images: Optional[Sequence[Any]] = None,
    audio: Optional[Sequence[Any]] = None,
    videos: Optional[Sequence[Any]] = None,
    files: Optional[Sequence[Any]] = None,
) -> Dict[str, List[Any]]:
    """The request's attachments as the ``media`` run option, or ValueError for anything not accepted.

    Uploads arrive as Image/File objects; JSON ``images``/``files`` items are limited to inline base64
    ``content`` plus format, mime type and, for files, a filename. Service paths, remote references,
    unknown keys, metadata, audio and video are refused so nothing is dropped or fetched silently.
    Counts and sizes are checked by the harness, which sees Python callers and the queue worker too.
    """
    if audio or videos:
        raise ValueError("Sandbox inputs support images and files only")
    media: Dict[str, List[Any]] = {}
    for kind, items in (("images", images), ("files", files)):
        if items:
            media[kind] = [_attachment(item, kind, index) for index, item in enumerate(items)]
    return media


def request_attachments(
    form: Any,
    *,
    images: Sequence[Any] = (),
    audio: Sequence[Any] = (),
    videos: Sequence[Any] = (),
    files: Sequence[Any] = (),
) -> Dict[str, List[Any]]:
    """Attachments from a request: the uploads already read, plus the raw JSON ``images``,
    ``input_files``, ``audio`` and ``videos`` form fields.

    The generic route rebuilds those JSON fields into objects and silently drops unknown keys and
    media references, so they are read from the raw form here and validated as sent.
    """
    parts: Dict[str, List[Any]] = {
        "images": list(images),
        "audio": list(audio),
        "videos": list(videos),
        "files": list(files),
    }
    for field, target in (("images", "images"), ("audio", "audio"), ("videos", "videos"), ("input_files", "files")):
        raw = form.get(field)
        if raw is None or raw == "":
            continue
        if not isinstance(raw, str):
            raise ValueError(f"'{field}' must be a JSON array")
        try:
            decoded = json.loads(raw)
        except (TypeError, ValueError, RecursionError) as error:
            raise ValueError(f"'{field}' must be a JSON array") from error
        if not isinstance(decoded, list):
            raise ValueError(f"'{field}' must be a JSON array")
        parts[target].extend(decoded)
    return sandbox_attachments(**parts)


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
    registered = await worker._aresolve_job_component({"component_type": "agent", "component_id": agent.get_id()})
    if registered is not agent:
        raise ValueError("Sandbox submissions must use the registered agent instance")
    from agno.sandbox import _harness

    options = _harness.submission(agent, input, kwargs)
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
        # The store stamps its own fields (such as session_seq) onto the payload; compare what was submitted.
        stored = existing.get("payload") or {}
        if {key: stored.get(key) for key in payload} != payload:
            raise HTTPException(status_code=409, detail="Idempotency-Key already has different input or options")
        return existing
    from agno.os.event_streams import get_event_stream
    from agno.run.base import RunStatus

    with contextlib.suppress(Exception):
        # Fail-open: the queue row is already committed - a Redis blip
        # must not fail an accepted submission (tails degrade gracefully)
        await get_event_stream().register_run(job["id"], RunStatus.pending)
    await aprepare_accepted_or_abort(worker, agent, "agent", job["id"], session_id, user_id, input)
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
    attachments: Optional[Dict[str, List[Any]]] = None,
) -> Any:
    if version is not None:
        raise HTTPException(
            status_code=400,
            detail="Sandboxed runs use the registered agent only; version pinning is not supported",
        )
    if kwargs.keys() & {"media", "sandbox_media"}:
        raise HTTPException(
            status_code=400, detail="'media' and 'sandbox_media' are reserved; send files or input_files"
        )
    if attachments:
        kwargs = {**kwargs, "media": attachments}
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
    delay = 0.1
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
        await asyncio.sleep(delay)
        delay = min(delay * 2, 1.0)
