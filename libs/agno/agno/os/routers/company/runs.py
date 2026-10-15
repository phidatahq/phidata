"""Task run routes: authorize, then enter the existing executor route and queue."""

from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.responses import JSONResponse, Response

from agno.company.execution import _call, _executor, _task_input, _task_submission
from agno.company.manager import AsyncCompanyManager, CompanyManager
from agno.db.base import AsyncBaseDb
from agno.db.schemas.tasks import task_run_id
from agno.os.auth import get_authentication_dependency
from agno.os.job_queue import ticket_status_to_api
from agno.os.middleware.user_scope import get_scoped_user_id
from agno.os.routers.company.schema import TaskRunCreate
from agno.os.routers.run_permissions import _require_endpoint_permission
from agno.os.schema import PaginatedResponse, PaginationInfo


async def _run_route(
    request: Request,
    path: str,
    method: str,
    form: Optional[Dict[str, str]] = None,
    key: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Response:
    """Enter the real FastAPI route with its dependencies and trusted caller state.

    Only transport authentication headers are retained. Runtime overrides from
    middleware or a Task request cannot become executor input.
    """
    body = urlencode(form or {}).encode()
    headers = [(k, v) for k, v in request.scope["headers"] if k.lower() in {b"authorization", b"cookie", b"x-api-key"}]
    headers += [(b"content-type", b"application/x-www-form-urlencoded"), (b"content-length", str(len(body)).encode())]
    if key:
        headers.append((b"idempotency-key", key.encode()))
    state = dict(request.scope.get("state") or {})
    for name in ("session_id", "session_state", "dependencies", "metadata"):
        state.pop(name, None)
    scope = {
        **request.scope,
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "headers": headers,
        "query_string": urlencode({"session_id": session_id}).encode() if session_id else b"",
        "state": state,
    }
    for name in ("route", "endpoint", "path_params"):
        scope.pop(name, None)
    messages = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    await request.app.router(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    content = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return Response(content, status_code=start["status"], media_type="application/json")


def get_company_runs_router(os: Any) -> APIRouter:
    router = APIRouter(prefix="/company", tags=["Company execution"])
    auth = get_authentication_dependency(os.settings)
    db = os._company_db
    manager = (
        AsyncCompanyManager(db, os.registry)
        if isinstance(db, AsyncBaseDb)
        else CompanyManager(db, os.registry)
        if db
        else None
    )

    async def task(task_id: str) -> Dict[str, Any]:
        if db is None:
            raise HTTPException(503, "Company requires a database")
        try:
            value = await _call(db, "get_task", task_id)
        except NotImplementedError:
            raise HTTPException(503, "Company execution is not supported by the configured database")
        if value is None:
            raise HTTPException(404, "Task not found")
        return value

    def executor(value: Dict[str, Any]):
        try:
            return _executor(os.registry, value["executor_type"], value["executor_id"])
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    def worker(request: Request):
        queue = getattr(request.app.state, "queue_worker", None)
        if queue is None:
            raise HTTPException(503, "Company execution requires the durable queue")
        return queue

    def endpoint(value: Dict[str, Any]):
        resource = {"agent": "agents", "team": "teams", "workflow": "workflows"}[value["executor_type"]]
        return f"/{resource}/{quote(value['executor_id'], safe='')}/runs"

    def run_database(value: Dict[str, Any]):
        store_ids = [entry.get("run_db_id") for entry in value["transitions"] if entry.get("attempt")]
        if store_ids and store_ids[0]:
            stores = list({id(store): store for store in os.dbs.get(store_ids[0], [])}.values())
            if len(stores) == 1:
                return stores[0]
            raise HTTPException(503, "Task session database is unavailable or ambiguous")
        return getattr(executor(value), "db", None)

    @router.post("/tasks/{task_id}/runs", status_code=202)
    async def start(task_id: str, request: Request, body: TaskRunCreate = TaskRunCreate(), _: bool = Depends(auth)):
        value = await task(task_id)
        component = executor(value)
        path = endpoint(value)
        await _require_endpoint_permission(request, path, "POST", action="accept")
        queue = worker(request)
        run_id = task_run_id(task_id, body.attempt)
        existing = await queue.store.get_job(run_id)
        if existing is not None:
            if (existing.get("payload") or {}).get("company_task_id") != task_id:
                raise HTTPException(409, "Run identifier conflicts with another submission")
            return JSONResponse(
                {
                    "run_id": run_id,
                    "session_id": existing["session_id"],
                    "status": ticket_status_to_api(existing["status"]),
                },
                status_code=202,
            )
        if value["status"] not in {"ready", "in_progress"} or not value.get("executor_id"):
            raise HTTPException(409, "Only accepted work can be started")
        run_db = getattr(component, "db", None)
        if run_db is None:
            raise HTTPException(409, "Task executor requires a database for durable runs")
        if value.get("job_id") and run_database(value) is not run_db:
            raise HTTPException(409, "A Task session must stay in its original executor database")
        caller = get_scoped_user_id(request) or getattr(request.state, "user_id", None)
        # The ordinary run route owns session permissions, including on revisions.
        from agno.db.base import SessionType
        from agno.os.middleware.user_scope import assert_session_writable, caller_is_admin

        await assert_session_writable(
            run_db,
            value.get("session_id"),
            caller or getattr(component, "user_id", None),
            session_type=SessionType(value["executor_type"]),
            is_admin=caller_is_admin(request),
        )
        if value.get("job_id") and value["job_id"] != run_id:
            previous = await queue.store.get_job(value["job_id"])
            if previous is None or previous["status"] not in {"failed", "cancelled", "completed"}:
                raise HTTPException(409, "The previous Task run is still active")
            if previous["status"] == "completed" and not any(
                entry.get("from") == "in_review" and entry.get("target") == "in_progress"
                for entry in value["transitions"]
            ):
                raise HTTPException(409, "Request revisions before starting another successful attempt")
        message = await _task_input(manager, value)
        if value.get("job_id") != run_id:
            try:
                reserved = await _call(
                    db,
                    "start_task_run",
                    task_id,
                    body.attempt,
                    value["transitions"],
                    user_id=caller,
                    run_db_id=run_db.id,
                )
            except ValueError as exc:
                raise HTTPException(409, str(exc))
            if reserved is None:
                value = await task(task_id)
                if value.get("job_id") != run_id:
                    raise HTTPException(409, "Task changed while starting")
            else:
                value = reserved
        starters = [entry for entry in value["transitions"] if entry.get("attempt") == body.attempt]
        if not starters or starters[-1].get("user_id") != caller:
            raise HTTPException(409, "The original starter must retry the pending submission")
        token = _task_submission.set({"db": db, "task": value})
        try:
            return await _run_route(
                request,
                path,
                "POST",
                {"message": message, "stream": "false", "background": "true", "session_id": value["session_id"]},
                key=f"company:{task_id}:{body.attempt}",
            )
        finally:
            _task_submission.reset(token)

    @router.get("/tasks/{task_id}/runs", response_model=PaginatedResponse[Dict[str, Any]])
    async def runs(
        task_id: str,
        request: Request,
        limit: int = Query(20, ge=1, le=1000),
        page: int = Query(1, ge=1),
        _: bool = Depends(auth),
    ):
        get_scoped_user_id(request)
        value = await task(task_id)
        if not value.get("job_id"):
            rows, total = [], 0
        else:
            run_db = run_database(value)
            if run_db is None:
                raise HTTPException(503, "Task run database is unavailable")
            rows, total = await _call(
                run_db, "get_runs", session_id=value["session_id"], limit=limit, page=page, deserialize=False
            )
        return PaginatedResponse(
            data=rows,
            meta=PaginationInfo(page=page, limit=limit, total_count=total, total_pages=(total + limit - 1) // limit),
        )

    async def company_run(run_id: str, request: Request):
        job = await worker(request).store.get_job(run_id)
        task_id = (job.get("payload") or {}).get("company_task_id") if job else None
        if not task_id:
            raise HTTPException(404, "Company run not found")
        value = await task(task_id)
        return job, value

    @router.get("/runs/{run_id}")
    async def get_run(run_id: str, request: Request, _: bool = Depends(auth)):
        get_scoped_user_id(request)
        job, value = await company_run(run_id, request)
        result = await _call(run_database(value), "get_run", run_id, deserialize=False)
        return result or {
            "run_id": run_id,
            "session_id": job["session_id"],
            "status": ticket_status_to_api(job["status"]),
            "content": job.get("error"),
        }

    @router.post("/runs/{run_id}/cancel")
    async def cancel(run_id: str, request: Request, _: bool = Depends(auth)):
        get_scoped_user_id(request)
        job, _task = await company_run(run_id, request)
        value = {"executor_type": job["component_type"], "executor_id": job["component_id"]}
        executor(value)
        return await _run_route(
            request, endpoint(value) + f"/{quote(run_id, safe='')}/cancel", "POST", session_id=job["session_id"]
        )

    @router.get("/attention")
    async def attention(request: Request, product_id: Optional[str] = None, _: bool = Depends(auth)):
        get_scoped_user_id(request)
        if manager is None:
            raise HTTPException(503, "Company requires a database")
        try:
            return await _attention(manager, product_id)
        except NotImplementedError:
            raise HTTPException(503, "Company tasks are not supported by the configured database")

    return router


async def _attention(manager: Any, product_id: Optional[str]):
    import asyncio

    return (
        await manager.attention(product_id)
        if isinstance(manager, AsyncCompanyManager)
        else await asyncio.to_thread(manager.attention, product_id)
    )
