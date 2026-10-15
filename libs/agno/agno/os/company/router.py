from functools import wraps
from typing import List

from fastapi import APIRouter, HTTPException, Query, Response

from agno.os.company.schemas import Product, ProductCreate, ProductUpdate
from agno.os.company.service import (
    CompanyAuthenticationError,
    CompanyService,
    ProductConflictError,
    ProductNotFoundError,
)
from agno.os.company.storage import CompanySchemaError


def _http_errors(function):
    @wraps(function)
    async def wrapped(*args, **kwargs):
        try:
            return await function(*args, **kwargs)
        except CompanyAuthenticationError as exc:
            raise HTTPException(401, str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except ProductNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ProductConflictError as exc:
            raise HTTPException(409, str(exc)) from exc
        except CompanySchemaError as exc:
            raise HTTPException(503, str(exc)) from exc

    return wrapped


def get_company_router(service: CompanyService) -> APIRouter:
    router = APIRouter(prefix="/company/v1/products", tags=["Company"])

    @router.post("", response_model=Product, status_code=201)
    @_http_errors
    async def create_product(body: ProductCreate) -> Product:
        return await service.acreate_product(body)

    @router.get("", response_model=List[Product])
    @_http_errors
    async def list_products(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> List[Product]:
        return await service.alist_products(limit=limit, offset=offset)

    @router.get("/{product_id}", response_model=Product)
    @_http_errors
    async def get_product(product_id: str) -> Product:
        return await service.aget_product(product_id)

    @router.patch("/{product_id}", response_model=Product)
    @_http_errors
    async def update_product(product_id: str, body: ProductUpdate) -> Product:
        return await service.aupdate_product(product_id, body)

    @router.delete("/{product_id}", status_code=204, response_class=Response)
    @_http_errors
    async def delete_product(product_id: str, expected_version: int = Query(..., ge=1)) -> Response:
        await service.adelete_product(product_id, expected_version=expected_version)
        return Response(status_code=204)

    return router
