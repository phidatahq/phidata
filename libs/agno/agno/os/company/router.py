"""Thin Company routes using trusted AgentOS identity and service permissions."""

from contextlib import contextmanager
from typing import Any, Iterator, Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from agno.db.base import AsyncBaseDb, BaseDb
from agno.db.schemas.company import CompanyConflict, CompanyForbidden, CompanyNotFound
from agno.os.company.async_service import AsyncCompanyService
from agno.os.company.schemas import (
    MemberList,
    MemberPut,
    MemberResponse,
    ProductCreate,
    ProductList,
    ProductResponse,
    ProductUpdate,
    ProductVersion,
)
from agno.os.company.service import CompanyService

COMPANY_SCOPE_MAPPINGS = {
    "GET /company/v1/products": ["company:read"],
    "GET /company/v1/products/*": ["company:read"],
    "POST /company/v1/products": ["company:write"],
    "POST /company/v1/products/*": ["company:write"],
    "PATCH /company/v1/products/*": ["company:write"],
    "PUT /company/v1/products/*": ["company:write"],
    "DELETE /company/v1/products/*": ["company:write"],
}


def _identity(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not getattr(request.state, "authenticated", False) or not isinstance(user_id, str) or not user_id:
        raise HTTPException(401, "Company requires an authenticated user")
    return user_id


@contextmanager
def _errors() -> Iterator[None]:
    try:
        yield
    except CompanyNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except CompanyForbidden as exc:
        raise HTTPException(403, str(exc)) from exc
    except CompanyConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def get_company_router(db: Union[BaseDb, AsyncBaseDb]) -> APIRouter:
    router = APIRouter(prefix="/company/v1", tags=["Company"])
    sync_service = CompanyService(db) if isinstance(db, BaseDb) else None
    async_service = AsyncCompanyService(db) if isinstance(db, AsyncBaseDb) else None

    @router.post("/products", response_model=ProductResponse)
    async def create_product(body: ProductCreate, user_id: str = Depends(_identity)) -> Any:
        with _errors():
            if async_service is not None:
                result = await async_service.create_product(user_id, body.name, body.purpose)
            else:
                assert sync_service is not None
                result = await run_in_threadpool(sync_service.create_product, user_id, body.name, body.purpose)
            return result

    @router.get("/products", response_model=ProductList)
    async def list_products(
        status: Optional[Literal["active", "archived"]] = None,
        limit: int = Query(50, ge=1, le=100),
        page: int = Query(1, ge=1),
        user_id: str = Depends(_identity),
    ) -> Any:
        with _errors():
            if async_service is not None:
                result = await async_service.list_products(user_id, status=status, limit=limit, page=page)
            else:
                assert sync_service is not None
                result = await run_in_threadpool(
                    sync_service.list_products, user_id, status=status, limit=limit, page=page
                )
            return {"data": result}

    @router.get("/products/{product_id}", response_model=ProductResponse)
    async def get_product(product_id: str, user_id: str = Depends(_identity)) -> Any:
        with _errors():
            if async_service is not None:
                result = await async_service.get_product(user_id, product_id)
            else:
                assert sync_service is not None
                result = await run_in_threadpool(sync_service.get_product, user_id, product_id)
            return result

    @router.patch("/products/{product_id}", response_model=ProductResponse)
    async def update_product(product_id: str, body: ProductUpdate, user_id: str = Depends(_identity)) -> Any:
        with _errors():
            if async_service is not None:
                result = await async_service.update_product(
                    user_id, product_id, body.expected_version, name=body.name, purpose=body.purpose
                )
            else:
                assert sync_service is not None
                result = await run_in_threadpool(
                    sync_service.update_product,
                    user_id,
                    product_id,
                    body.expected_version,
                    name=body.name,
                    purpose=body.purpose,
                )
            return result

    @router.post("/products/{product_id}/archive", response_model=ProductResponse)
    async def archive_product(product_id: str, body: ProductVersion, user_id: str = Depends(_identity)) -> Any:
        with _errors():
            if async_service is not None:
                result = await async_service.archive_product(user_id, product_id, body.expected_version)
            else:
                assert sync_service is not None
                result = await run_in_threadpool(
                    sync_service.archive_product, user_id, product_id, body.expected_version
                )
            return result

    @router.post("/products/{product_id}/restore", response_model=ProductResponse)
    async def restore_product(product_id: str, body: ProductVersion, user_id: str = Depends(_identity)) -> Any:
        with _errors():
            if async_service is not None:
                result = await async_service.restore_product(user_id, product_id, body.expected_version)
            else:
                assert sync_service is not None
                result = await run_in_threadpool(
                    sync_service.restore_product, user_id, product_id, body.expected_version
                )
            return result

    @router.get("/products/{product_id}/members", response_model=MemberList)
    async def list_members(product_id: str, user_id: str = Depends(_identity)) -> Any:
        with _errors():
            if async_service is not None:
                result = await async_service.list_members(user_id, product_id)
            else:
                assert sync_service is not None
                result = await run_in_threadpool(sync_service.list_members, user_id, product_id)
            return {"data": result}

    @router.put("/products/{product_id}/members/{member_id}", response_model=MemberResponse)
    async def add_member(product_id: str, member_id: str, body: MemberPut, user_id: str = Depends(_identity)) -> Any:
        with _errors():
            if async_service is not None:
                result = await async_service.add_member(user_id, product_id, member_id, body.role)
            else:
                assert sync_service is not None
                result = await run_in_threadpool(sync_service.add_member, user_id, product_id, member_id, body.role)
            return result

    @router.delete("/products/{product_id}/members/{member_id}", status_code=204, response_model=None)
    async def remove_member(product_id: str, member_id: str, user_id: str = Depends(_identity)) -> Any:
        with _errors():
            if async_service is not None:
                await async_service.remove_member(user_id, product_id, member_id)
            else:
                assert sync_service is not None
                await run_in_threadpool(sync_service.remove_member, user_id, product_id, member_id)
            return Response(status_code=204)

    return router
