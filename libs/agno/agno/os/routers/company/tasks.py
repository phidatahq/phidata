"""Company-wide task reads with owner-scoped writes, following Products."""

import asyncio
from typing import Any, Dict, Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from agno.company.manager import AsyncCompanyManager, CompanyManager
from agno.db.base import AsyncBaseDb, BaseDb
from agno.db.schemas.scheduler import RUN_ENDPOINT_RE
from agno.os.auth import get_authentication_dependency
from agno.os.middleware.user_scope import get_scoped_user_id
from agno.os.routers.company.schema import TaskCreate, TaskResponse, TaskStatus, TaskTransition, TaskUpdate
from agno.os.schema import PaginatedResponse, PaginationInfo
from agno.os.scopes import AgentOSScope, has_required_scopes
from agno.os.settings import AgnoAPISettings
from agno.tools.scheduler import _manager_member_refusal


def _require_write_ownership(existing: Dict[str, Any], user_id: Optional[str]) -> None:
    """Check the scoped caller against the owner after a company-wide read."""
    if user_id is not None and existing.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Cannot modify task owned by another user")


def _require_endpoint_permission(request: Request, endpoint: str, method: str) -> None:
    """Apply the scheduler's target permission check to Task acceptance.

    Task write permission does not grant executor run permission. Non-run
    executors require admin access under the scope-based authorization plane.
    """
    from agno.os.auth import build_insufficient_permissions_detail, caller_scopes_are_authoritative

    private_target = _manager_member_refusal(endpoint)
    if private_target:
        raise HTTPException(status_code=409, detail=private_target)

    if not getattr(request.state, "authorization_enabled", False):
        return

    caller_scopes = getattr(request.state, "scopes", [])
    admin_scope_raw = getattr(request.state, "admin_scope", None) or getattr(request.app.state, "admin_scope", None)
    admin_scope = admin_scope_raw if isinstance(admin_scope_raw, str) else None

    match = RUN_ENDPOINT_RE.match(endpoint) if method.upper() == "POST" else None

    if not caller_scopes_are_authoritative(request):
        # The token's scopes are NOT the authority here (a managed-roles/ReBAC/custom
        # plane governs access, and ignores them). Decide the target the same way its
        # own route gate would -- through the configured provider -- so `tasks:write`
        # cannot accept a component the caller may not run themselves.
        from agno.os.auth import resolve_authorization_provider
        from agno.os.authz.provider import AuthorizationContext

        if match is None:
            # A non-run target is admin-only; a managed/ReBAC plane exposes no generic
            # "is admin" question to pose here, so fail closed.
            raise HTTPException(
                status_code=403,
                detail="Accepting a non-run endpoint requires a scope-based authorization plane",
            )
        resource_type, resource_id = match.group(1), match.group(2)
        provider = resolve_authorization_provider(request)
        ctx = AuthorizationContext(
            principal_id=getattr(request.state, "user_id", None),
            scopes=list(caller_scopes),
            claims=getattr(request.state, "claims", None) or {},
            resource_type=resource_type,
            resource_id=resource_id,
            action="run",
            admin_scope=admin_scope,
        )
        if not provider.check(ctx):
            raise HTTPException(status_code=403, detail=build_insufficient_permissions_detail([f"{resource_type}:run"]))
        return

    if match is None:
        admin = admin_scope or AgentOSScope.ADMIN.value
        if not has_required_scopes(list(caller_scopes), [admin], admin_scope=admin_scope):
            raise HTTPException(status_code=403, detail="Only admins can accept an endpoint that is not a run endpoint")
        return

    resource_type, resource_id = match.group(1), match.group(2)
    required_scope = f"{resource_type}:run"
    if not has_required_scopes(
        list(caller_scopes),
        [required_scope],
        resource_type=resource_type,
        resource_id=resource_id,
        admin_scope=admin_scope,
    ):
        raise HTTPException(status_code=403, detail=build_insufficient_permissions_detail([required_scope]))


def get_tasks_router(db: Optional[Union[BaseDb, AsyncBaseDb]], settings: AgnoAPISettings) -> APIRouter:
    """Build Task routes using native async storage or off-thread sync calls."""
    router = APIRouter(prefix="/company", tags=["Tasks"])
    auth_dependency = get_authentication_dependency(settings)
    manager = AsyncCompanyManager(db) if isinstance(db, AsyncBaseDb) else CompanyManager(db) if db is not None else None

    async def _call(
        method: Literal[
            "create_task", "get_task", "list_tasks", "update_task", "delete_task", "restore_task", "transition_task"
        ],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if manager is None:
            raise HTTPException(status_code=503, detail="Company requires a database")
        try:
            fn = getattr(manager, method)
            if isinstance(manager, AsyncCompanyManager):
                return await fn(*args, **kwargs)
            return await asyncio.to_thread(fn, *args, **kwargs)
        except NotImplementedError:
            raise HTTPException(status_code=503, detail="Company tasks not supported by the configured database")
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ValueError as exc:
            conflict = method == "transition_task" or str(exc) == "Accepted task scope requires a return to Backlog"
            raise HTTPException(status_code=409 if conflict else 422, detail=str(exc))

    async def _writable(task_id: str, user_id: Optional[str], include_deleted: bool = False) -> Dict[str, Any]:
        existing = await _call("get_task", task_id, user_id=None, include_deleted=include_deleted)
        if existing is None:
            raise HTTPException(status_code=404, detail="Task not found")
        _require_write_ownership(existing, user_id)
        return existing

    @router.get("/tasks", response_model=PaginatedResponse[TaskResponse])
    async def list_tasks(
        limit: int = Query(20, ge=1, le=1000),
        page: int = Query(1, ge=1),
        include_deleted: bool = Query(False),
        product_id: Optional[str] = Query(None),
        status: Optional[TaskStatus] = Query(None),
        project_id: Optional[str] = Query(None),
        _: bool = Depends(auth_dependency),
    ) -> PaginatedResponse[TaskResponse]:
        rows, total = await _call(
            "list_tasks",
            user_id=None,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            product_id=product_id,
            status=status,
            project_id=project_id,
        )
        return PaginatedResponse(
            data=[TaskResponse(**row) for row in rows],
            meta=PaginationInfo(page=page, limit=limit, total_count=total, total_pages=(total + limit - 1) // limit),
        )

    @router.post("/tasks", response_model=TaskResponse, status_code=201)
    async def create_task(body: TaskCreate, request: Request, _: bool = Depends(auth_dependency)) -> Dict[str, Any]:
        user_id = get_scoped_user_id(request)
        return await _call(
            "create_task",
            **body.model_dump(),
            user_id=user_id or getattr(request.state, "user_id", None),
        )

    @router.get("/tasks/{task_id}", response_model=TaskResponse)
    async def get_task(
        task_id: str, include_deleted: bool = Query(False), _: bool = Depends(auth_dependency)
    ) -> Dict[str, Any]:
        task = await _call("get_task", task_id, user_id=None, include_deleted=include_deleted)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @router.patch("/tasks/{task_id}", response_model=TaskResponse)
    async def update_task(
        task_id: str, body: TaskUpdate, request: Request, _: bool = Depends(auth_dependency)
    ) -> Dict[str, Any]:
        user_id = get_scoped_user_id(request)
        existing = await _writable(task_id, user_id)
        fields = body.model_dump(exclude_unset=True)
        if not fields:
            return existing
        task = await _call("update_task", task_id, user_id=user_id, **fields)
        if task is None:
            raise HTTPException(status_code=409, detail="Task changed while updating")
        return task

    @router.delete("/tasks/{task_id}", status_code=204)
    async def delete_task(task_id: str, request: Request, _: bool = Depends(auth_dependency)) -> None:
        user_id = get_scoped_user_id(request)
        await _writable(task_id, user_id)
        if not await _call("delete_task", task_id, user_id=user_id):
            raise HTTPException(status_code=404, detail="Task not found")

    @router.post("/tasks/{task_id}/restore", response_model=TaskResponse)
    async def restore_task(task_id: str, request: Request, _: bool = Depends(auth_dependency)) -> Dict[str, Any]:
        user_id = get_scoped_user_id(request)
        existing = await _writable(task_id, user_id, include_deleted=True)
        if existing.get("deleted_at") is None:
            raise HTTPException(status_code=409, detail="Task is not archived")
        task = await _call("restore_task", task_id, user_id=user_id)
        if task is None:
            raise HTTPException(status_code=409, detail="Task is not archived")
        return task

    @router.post("/tasks/{task_id}/transitions", response_model=TaskResponse)
    async def transition_task(
        task_id: str, body: TaskTransition, request: Request, _: bool = Depends(auth_dependency)
    ) -> Dict[str, Any]:
        user_id = get_scoped_user_id(request)
        await _writable(task_id, user_id)
        if body.target == "ready":
            assert body.executor_type is not None  # Validated by TaskTransition.
            resource = {"agent": "agents", "team": "teams", "workflow": "workflows", "engineering": "engineering"}[
                body.executor_type
            ]
            _require_endpoint_permission(request, f"/{resource}/{body.executor_id}/runs", "POST")
        record = await _call(
            "transition_task",
            task_id,
            **body.model_dump(),
            user_id=user_id,
            accepted_by=getattr(request.state, "user_id", None),
        )
        if record is None:
            raise HTTPException(status_code=409, detail="Task changed while transitioning")
        return record

    return router
