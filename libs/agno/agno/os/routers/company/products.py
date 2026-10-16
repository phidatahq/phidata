"""Product CRUD routes for the opt-in Company domain.

Products are company-wide records: every caller with the read scope sees every
Product, whether or not user isolation is on. Isolation scopes writes only, so a
non-admin caller can change a Product only when they own it, as with published
components.
"""

import asyncio
from typing import Any, Dict, Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from agno.company.manager import AsyncCompanyManager, CompanyManager
from agno.db.base import AsyncBaseDb, BaseDb
from agno.os.auth import get_authentication_dependency
from agno.os.middleware.user_scope import get_scoped_user_id
from agno.os.routers.company.schema import ProductCreate, ProductResponse, ProductUpdate
from agno.os.schema import PaginatedResponse, PaginationInfo
from agno.os.settings import AgnoAPISettings


def _require_write_ownership(existing: Dict[str, Any], user_id: Optional[str]) -> None:
    """Refuse a scoped caller writing to a Product it does not own.

    Reads are company-wide, so the row is always visible; a scoped caller that is
    not the owner gets an honest 403 rather than a 404. An unscoped caller
    (isolation off, or admin) may write to any Product.
    """
    if user_id is None:
        return
    owner = existing.get("user_id")
    if owner is None:
        raise HTTPException(status_code=403, detail="Cannot modify unowned product")
    if owner != user_id:
        raise HTTPException(status_code=403, detail="Cannot modify product owned by another user")


def get_products_router(db: Optional[Union[BaseDb, AsyncBaseDb]], settings: AgnoAPISettings) -> APIRouter:
    """Build Product routes using native async storage or off-thread sync calls."""
    router = APIRouter(prefix="/company", tags=["Products"], dependencies=[Depends(get_scoped_user_id)])
    auth_dependency = get_authentication_dependency(settings)
    manager = AsyncCompanyManager(db) if isinstance(db, AsyncBaseDb) else CompanyManager(db) if db is not None else None

    async def _call(
        method: Literal["create", "get", "list", "update", "delete", "restore"], *args: Any, **kwargs: Any
    ) -> Any:
        if manager is None:
            raise HTTPException(status_code=503, detail="Company requires a database")
        try:
            fn = getattr(manager, method)
            if isinstance(manager, AsyncCompanyManager):
                result = await fn(*args, **kwargs)
            else:
                result = await asyncio.to_thread(fn, *args, **kwargs)
            if result is not None and method in {"create", "update", "restore"}:
                result = await _call("get", result["id"], include_deleted=True)
            return result
        except NotImplementedError:
            raise HTTPException(status_code=503, detail="Company products not supported by the configured database")
        except ValueError as exc:
            raise HTTPException(
                status_code=409 if method == "delete" else 422, detail=exc.args[0] if exc.args else str(exc)
            )

    async def _writable(product_id: str, user_id: Optional[str], include_deleted: bool = False) -> Dict[str, Any]:
        # Company-wide read first, then the ownership check against the scoped caller.
        existing = await _call("get", product_id, user_id=None, include_deleted=include_deleted)
        if existing is None:
            raise HTTPException(status_code=404, detail="Product not found")
        _require_write_ownership(existing, user_id)
        return existing

    @router.get("/products", response_model=PaginatedResponse[ProductResponse])
    async def list_products(
        limit: int = Query(20, ge=1, le=1000),
        page: int = Query(1, ge=1),
        include_deleted: bool = Query(False),
        sort_by: Literal["created_at", "updated_at"] = Query("created_at"),
        sort_order: Literal["asc", "desc"] = Query("desc"),
        _: bool = Depends(auth_dependency),
    ) -> PaginatedResponse[ProductResponse]:
        rows, total = await _call(
            "list",
            user_id=None,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PaginatedResponse(
            data=[ProductResponse(**row) for row in rows],
            meta=PaginationInfo(page=page, limit=limit, total_count=total, total_pages=(total + limit - 1) // limit),
        )

    @router.post("/products", response_model=ProductResponse, status_code=201)
    async def create_product(
        body: ProductCreate, request: Request, _: bool = Depends(auth_dependency)
    ) -> Dict[str, Any]:
        user_id = get_scoped_user_id(request)
        return await _call("create", **body.model_dump(), user_id=user_id or getattr(request.state, "user_id", None))

    @router.get("/products/{product_id}", response_model=ProductResponse)
    async def get_product(
        product_id: str, include_deleted: bool = Query(False), _: bool = Depends(auth_dependency)
    ) -> Dict[str, Any]:
        product = await _call("get", product_id, user_id=None, include_deleted=include_deleted)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @router.patch("/products/{product_id}", response_model=ProductResponse)
    async def update_product(
        product_id: str, body: ProductUpdate, request: Request, _: bool = Depends(auth_dependency)
    ) -> Dict[str, Any]:
        user_id = get_scoped_user_id(request)
        existing = await _writable(product_id, user_id)
        fields = body.model_dump(exclude_unset=True)
        if not fields:
            return existing
        product = await _call("update", product_id, user_id=user_id, **fields)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @router.delete("/products/{product_id}", status_code=204)
    async def delete_product(product_id: str, request: Request, _: bool = Depends(auth_dependency)) -> Response:
        user_id = get_scoped_user_id(request)
        await _writable(product_id, user_id)
        try:
            archived = await _call("delete", product_id, user_id=user_id)
        except HTTPException as exc:
            if exc.status_code == 409 and isinstance(exc.detail, dict):
                # Keep the Task list structured through AgentOS's string error handler.
                return JSONResponse(status_code=409, content={"detail": exc.detail})
            raise
        if not archived:
            raise HTTPException(status_code=404, detail="Product not found")
        return Response(status_code=204)

    @router.post("/products/{product_id}/restore", response_model=ProductResponse)
    async def restore_product(product_id: str, request: Request, _: bool = Depends(auth_dependency)) -> Dict[str, Any]:
        user_id = get_scoped_user_id(request)
        existing = await _writable(product_id, user_id, include_deleted=True)
        if existing.get("deleted_at") is None:
            raise HTTPException(status_code=409, detail="Product is not archived")
        product = await _call("restore", product_id, user_id=user_id)
        if product is None:
            raise HTTPException(status_code=409, detail="Product is not archived")
        return product

    return router
