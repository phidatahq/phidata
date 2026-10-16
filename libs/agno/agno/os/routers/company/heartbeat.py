"""Sources, Routine schedule wrappers and blank-deployment setup."""

import asyncio
import inspect
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict

from agno.company.declarations import Product, Routine, Source
from agno.company.manager import AsyncCompanyManager, CompanyManager
from agno.company.routines import _routine_message, _schedule_fields
from agno.db.base import AsyncBaseDb
from agno.os.auth import get_authentication_dependency
from agno.os.middleware.user_scope import get_scoped_user_id
from agno.os.routers.company.products import _require_write_ownership
from agno.os.routers.schedules.router import get_schedule_router
from agno.os.routers.schedules.schema import ScheduleCreate, ScheduleResponse, ScheduleStateResponse, ScheduleUpdate
from agno.os.schema import PaginatedResponse, PaginationInfo


class SourceCreate(Source):
    product_id: str
    id: None = None


class RoutineCreate(Routine):
    product_id: str


class RoutineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instructions: Optional[str] = None
    cron_expr: Optional[str] = None
    timezone: Optional[str] = None
    auto_accept: Optional[bool] = None


class Setup(Product):
    id: None = None
    user_id: None = None


def get_heartbeat_router(agent_os: Any) -> APIRouter:
    router = APIRouter(prefix="/company", tags=["Company heartbeat"])
    db = agent_os._company_db
    manager = AsyncCompanyManager(db) if isinstance(db, AsyncBaseDb) else CompanyManager(db)
    auth = get_authentication_dependency(agent_os.settings)
    schedule_db = agent_os.db
    scheduler = get_schedule_router(
        schedule_db,
        agent_os.settings,
        agent_os.agents,
        agent_os.teams,
        agent_os.workflows,
        managed_by="company",
        company_reads=True,
    )
    handlers = {route.name: route.endpoint for route in scheduler.routes if isinstance(route, APIRoute)}

    async def call(fn, *args, **kwargs):
        if db is None:
            raise HTTPException(503, "Company requires a database")
        try:
            return (
                await fn(*args, **kwargs)
                if inspect.iscoroutinefunction(fn)
                else await asyncio.to_thread(fn, *args, **kwargs)
            )
        except NotImplementedError:
            raise HTTPException(503, "Company heartbeat not supported by the configured database")
        except LookupError as exc:
            raise HTTPException(404, str(exc))
        except PermissionError as exc:
            raise HTTPException(403, str(exc))
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    async def product(product_id, request):
        row = await call(manager.get, product_id)
        if row is None:
            raise HTTPException(404, "Product not found")
        _require_write_ownership(row, get_scoped_user_id(request))
        return row

    async def routine(routine_id, request):
        row = await call(handlers["get_schedule"], routine_id, request)
        if row.get("managed_by") != "company":
            raise HTTPException(404, "Routine not found")
        if request.method != "GET":
            _require_write_ownership(row, get_scoped_user_id(request))
        return row

    def page_response(rows, total, limit, page):
        return PaginatedResponse(
            data=rows,
            meta=PaginationInfo(page=page, limit=limit, total_count=total, total_pages=(total + limit - 1) // limit),
        )

    @router.get("/sources")
    async def list_sources(
        request: Request,
        product_id: Optional[str] = None,
        limit: int = Query(20, ge=1, le=1000),
        page: int = Query(1, ge=1),
        include_deleted: bool = False,
        _: bool = Depends(auth),
    ):
        get_scoped_user_id(request)
        rows, total = await call(
            manager.list_sources, product_id=product_id, limit=limit, page=page, include_deleted=include_deleted
        )
        return page_response(rows, total, limit, page)

    @router.post("/sources", status_code=201)
    async def create_source(body: SourceCreate, request: Request, _: bool = Depends(auth)):
        return await call(
            manager.create_source,
            **body.model_dump(exclude={"id"}),
            user_id=get_scoped_user_id(request) or getattr(request.state, "user_id", None),
            scoped_user_id=get_scoped_user_id(request),
        )

    @router.delete("/sources/{source_id}", status_code=204)
    async def delete_source(source_id: str, request: Request, _: bool = Depends(auth)):
        if not await call(manager.delete_source, source_id, user_id=get_scoped_user_id(request)):
            raise HTTPException(404, "Source not found")

    @router.post("/sources/{source_id}/restore")
    async def restore_source(source_id: str, request: Request, _: bool = Depends(auth)):
        row = await call(manager.get_source, source_id, include_deleted=True)
        if row is None:
            raise HTTPException(404, "Source not found")
        await product(row["product_id"], request)
        if row.get("deleted_at") is None:
            raise HTTPException(409, "Source is not archived")
        return await call(manager.restore_source, source_id, user_id=get_scoped_user_id(request))

    @router.get("/routines", response_model=PaginatedResponse[ScheduleResponse])
    async def list_routines(
        request: Request,
        product_id: Optional[str] = None,
        limit: int = Query(20, ge=1, le=1000),
        page: int = Query(1, ge=1),
        _: bool = Depends(auth),
    ):
        from agno.scheduler import ScheduleManager

        get_scoped_user_id(request)
        rows = await call(ScheduleManager(schedule_db).alist_all)
        selected = [
            row.to_dict()
            for row in rows
            if row.managed_by == "company"
            and (product_id is None or (row.payload or {}).get("metadata", {}).get("product_id") == product_id)
        ]
        return page_response(selected[(page - 1) * limit : page * limit], len(selected), limit, page)

    @router.post("/routines", status_code=201, response_model=ScheduleResponse)
    async def create_routine(body: RoutineCreate, request: Request, _: bool = Depends(auth)):
        await product(body.product_id, request)
        fields = await call(_schedule_fields, body.product_id, body, agent_os.registry)
        schedule = await call(ScheduleCreate, **fields)
        row = await call(handlers["create_schedule"], schedule, request)
        await call(db.add_product_routine, body.product_id, row["id"])
        return row

    @router.patch("/routines/{routine_id}", response_model=ScheduleResponse)
    async def update_routine(routine_id: str, body: RoutineUpdate, request: Request, _: bool = Depends(auth)):
        row = await routine(routine_id, request)
        await product(row["payload"]["metadata"]["product_id"], request)
        updates: Dict[str, Any] = body.model_dump(exclude_unset=True)
        if any(value is None for value in updates.values()):
            raise HTTPException(422, "Routine fields cannot be null")
        if updates.pop("auto_accept", False):
            raise HTTPException(422, "Automatic acceptance is not available")
        if "instructions" in updates:
            updates["payload"] = {
                **row["payload"],
                "message": _routine_message(row["payload"]["metadata"]["product_id"], updates.pop("instructions")),
            }
        update = await call(ScheduleUpdate, **updates)
        return await call(handlers["update_schedule"], routine_id, update, request)

    @router.post("/routines/{routine_id}/pause", response_model=ScheduleStateResponse)
    async def pause_routine(routine_id: str, request: Request, _: bool = Depends(auth)):
        row = await routine(routine_id, request)
        await product(row["payload"]["metadata"]["product_id"], request)
        return await call(handlers["disable_schedule"], routine_id, request)

    @router.post("/routines/{routine_id}/resume", response_model=ScheduleStateResponse)
    async def resume_routine(routine_id: str, request: Request, _: bool = Depends(auth)):
        row = await routine(routine_id, request)
        await product(row["payload"]["metadata"]["product_id"], request)
        return await call(handlers["enable_schedule"], routine_id, request)

    @router.get("/routines/{routine_id}/runs")
    async def routine_runs(
        routine_id: str,
        request: Request,
        limit: int = Query(20, ge=1, le=1000),
        page: int = Query(1, ge=1),
        _: bool = Depends(auth),
    ):
        await routine(routine_id, request)
        return await call(handlers["list_schedule_runs"], routine_id, request, limit=limit, page=page)

    @router.post("/setup", status_code=201)
    async def setup(body: Setup, request: Request, response: Response, _: bool = Depends(auth)):
        from agno.company.bootstrap import arehydrate_product
        from agno.os.routers.run_permissions import _require_endpoint_permission
        from agno.run.authorization import current_authorization

        owner = get_scoped_user_id(request) or getattr(request.state, "user_id", None)
        authority = current_authorization()
        if body.sources and authority is not None:
            await authority.arequire("sources", "write")
        if body.routines:
            if authority is not None:
                await authority.arequire("schedules", "write")
                await authority.arequire("routines", "write")
            for declaration in body.routines:
                fields = await call(_schedule_fields, "company-setup", declaration, agent_os.registry)
                await _require_endpoint_permission(request, fields["endpoint"], "POST")
        existing = await call(manager.get, "company-setup", include_deleted=True)
        if existing is not None:
            _require_write_ownership(existing, get_scoped_user_id(request))
            response.status_code = 200
        else:
            rows, _ = await call(manager.list, limit=1, include_deleted=True)
            if rows:
                raise HTTPException(409, "Company setup requires a deployment without Products")
        product_declaration = Product(**{**body.model_dump(), "id": "company-setup", "user_id": owner})
        return await call(
            arehydrate_product,
            db,
            product_declaration,
            agent_os.registry,
            schedule_db=schedule_db,
            scoped_user_id=get_scoped_user_id(request),
        )

    return router
