"""Company HTTP adapter. All policy and transactions live in the shared service."""

import re
from types import MappingProxyType
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError

from agno.os.auth import resolve_authorization_provider
from agno.os.company.policy import CompanyError, Principal
from agno.os.company.schemas import (
    Activity,
    Caller,
    Comment,
    CommentCreate,
    CompanySetup,
    FileWrite,
    ListQuery,
    MemberCreate,
    MemberPatch,
    Membership,
    Page,
    Product,
    ProductCreate,
    ProductPatch,
    Project,
    ProjectCreate,
    ProjectPatch,
    ProjectSummary,
    PullRequestReview,
    Reason,
    RunTask,
    Task,
    TaskCreate,
    TaskPatch,
    TaskSchedule,
    Transition,
)
from agno.os.company.service import CompanyService
from agno.os.middleware.jwt import _AUTH_COMPLETE_ATTR


def principal_from_request(request: Request) -> Principal:
    if (
        not getattr(request.state, _AUTH_COMPLETE_ATTR, False)
        or not getattr(request.state, "authorization_enabled", False)
        or not getattr(request.state, "claims", {}).get("sub")
        or not getattr(request.state, "user_id", None)
        or getattr(request.state, "is_service_account", False)
    ):
        raise CompanyError(401, "unauthenticated", "A verified human JWT is required")
    return Principal(
        id=request.state.user_id,
        provider=resolve_authorization_provider(request),
        scopes=tuple(getattr(request.state, "scopes", [])),
        claims=MappingProxyType(dict(getattr(request.state, "claims", {}))),
    )


class CompanyRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def wrapped(request: Request) -> Response:
            supplied = request.headers.get("X-Request-ID", "")
            request.state.company_request_id = getattr(request.state, "company_request_id", None) or (
                supplied if re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", supplied) else str(uuid4())
            )
            rid = request.state.company_request_id
            try:
                response = await handler(request)
            except CompanyError as exc:
                response = JSONResponse(
                    status_code=exc.status,
                    content={"error": {"code": exc.code, "message": exc.message, "details": {}}, "request_id": rid},
                )
            except (RequestValidationError, ValidationError):
                response = JSONResponse(
                    status_code=422,
                    content={
                        "error": {"code": "validation_error", "message": "Invalid request fields", "details": {}},
                        "request_id": rid,
                    },
                )
            response.headers["X-Request-ID"] = rid
            response.headers["Cache-Control"] = "no-store"
            return response

        return wrapped


def mutation_headers(
    request: Request,
    idempotency_key: Optional[str] = Header(default=None),
    if_match: Optional[str] = Header(default=None),
) -> dict:
    if not idempotency_key:
        raise CompanyError(428, "idempotency_required", "Idempotency-Key is required")
    version = None
    if if_match is not None:
        if not re.fullmatch(r'"[1-9][0-9]*"', if_match):
            raise CompanyError(422, "invalid_precondition", "If-Match must be a quoted positive version")
        version = int(if_match.strip('"'))
    return {"request_id": request.state.company_request_id, "idempotency_key": idempotency_key, "version": version}


def _etag(response: Response, result: dict) -> dict:
    if "version" in result:
        response.headers["ETag"] = f'"{result["version"]}"'
    return result


def get_company_router(service: CompanyService) -> APIRouter:
    router = APIRouter(prefix="/company/v1", tags=["Company"], route_class=CompanyRoute)

    @router.post("/setup", response_model=Product)
    async def setup_agentos(
        data: CompanySetup,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        headers.pop("version", None)
        return _etag(response, await service.asetup_agentos(principal=principal, data=data, **headers))

    @router.get("/files")
    async def list_files(
        product_id: Optional[UUID] = None,
        directory: str = "",
        query: str = "",
        after: str = "",
        limit: int = 50,
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return await service.files.alist(
            principal=principal,
            product_id=str(product_id) if product_id else None,
            directory=directory,
            query=query,
            after=after,
            limit=limit,
        )

    @router.get("/files/content")
    async def read_file(
        path: str, product_id: Optional[UUID] = None, principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return await service.files.aread(
            principal=principal, product_id=str(product_id) if product_id else None, path=path
        )

    @router.put("/files/content")
    async def write_file(
        data: FileWrite,
        product_id: Optional[UUID] = None,
        principal: Principal = Depends(principal_from_request),
        headers: dict = Depends(mutation_headers),
    ) -> Any:
        return await service.files.awrite(
            principal=principal,
            product_id=str(product_id) if product_id else None,
            **data.model_dump(),
            idempotency_key=headers["idempotency_key"],
            request_id=headers["request_id"],
        )

    @router.get("/me", response_model=Caller)
    async def me(principal: Principal = Depends(principal_from_request)) -> Any:
        return await service.aget_me(principal=principal)

    @router.get("/products", response_model=Page[Product])
    async def list_products(
        query: ListQuery = Depends(), principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return await service.alist_products(principal=principal, query=query)

    @router.get("/products/{product_id}", response_model=Product)
    async def get_product(
        product_id: UUID, response: Response, principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return _etag(response, await service.aget_product(principal=principal, product_id=str(product_id)))

    @router.post("/products", response_model=Product, status_code=201)
    async def create_product(
        data: ProductCreate,
        request: Request,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        headers.pop("version", None)
        return _etag(response, await service.acreate_product(principal=principal, data=data, **headers))

    @router.patch("/products/{product_id}", response_model=Product, status_code=200)
    async def update_product(
        data: ProductPatch,
        request: Request,
        response: Response,
        product_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.aupdate_product(principal=principal, data=data, **headers, product_id=str(product_id)),
        )

    @router.post("/products/{product_id}/archive", response_model=Product, status_code=200)
    async def archive_product(
        data: Reason,
        request: Request,
        response: Response,
        product_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.aarchive_product(principal=principal, data=data, **headers, product_id=str(product_id)),
        )

    @router.post("/products/{product_id}/restore", response_model=Product, status_code=200)
    async def restore_product(
        data: Reason,
        request: Request,
        response: Response,
        product_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.arestore_product(principal=principal, data=data, **headers, product_id=str(product_id)),
        )

    @router.get("/projects", response_model=Page[Project])
    async def list_projects(
        query: ListQuery = Depends(), principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return await service.alist_projects(principal=principal, query=query)

    @router.get("/projects/{project_id}", response_model=Project)
    async def get_project(
        project_id: UUID, response: Response, principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return _etag(response, await service.aget_project(principal=principal, project_id=str(project_id)))

    @router.post("/products/{product_id}/projects", response_model=Project, status_code=201)
    async def create_project(
        data: ProjectCreate,
        request: Request,
        response: Response,
        product_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        headers.pop("version", None)
        return _etag(
            response,
            await service.acreate_project(principal=principal, data=data, **headers, product_id=str(product_id)),
        )

    @router.patch("/projects/{project_id}", response_model=Project, status_code=200)
    async def update_project(
        data: ProjectPatch,
        request: Request,
        response: Response,
        project_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.aupdate_project(principal=principal, data=data, **headers, project_id=str(project_id)),
        )

    @router.post("/projects/{project_id}/comments", response_model=Comment, status_code=201)
    async def add_comment_project(
        data: CommentCreate,
        request: Request,
        response: Response,
        project_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        headers.pop("version", None)
        return _etag(
            response,
            await service.aadd_comment_project(principal=principal, data=data, **headers, project_id=str(project_id)),
        )

    @router.get("/projects/{project_id}/comments", response_model=Page[Comment])
    async def list_project_comments(
        project_id: UUID, query: ListQuery = Depends(), principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return await service.alist_comments(principal=principal, kind="project", record_id=str(project_id), query=query)

    @router.get("/tasks", response_model=Page[Task])
    async def list_tasks(query: ListQuery = Depends(), principal: Principal = Depends(principal_from_request)) -> Any:
        return await service.alist_tasks(principal=principal, query=query)

    @router.get("/tasks/{task_id}", response_model=Task)
    async def get_task(
        task_id: UUID,
        response: Response,
        project_id: Optional[UUID] = None,
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.aget_task(
                principal=principal, task_id=str(task_id), project_id=str(project_id) if project_id else None
            ),
        )

    @router.post("/products/{product_id}/tasks", response_model=Task, status_code=201)
    async def create_task(
        data: TaskCreate,
        request: Request,
        response: Response,
        product_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        headers.pop("version", None)
        return _etag(
            response, await service.acreate_task(principal=principal, data=data, **headers, product_id=str(product_id))
        )

    @router.patch("/tasks/{task_id}", response_model=Task, status_code=200)
    async def update_task(
        data: TaskPatch,
        request: Request,
        response: Response,
        task_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response, await service.aupdate_task(principal=principal, data=data, **headers, task_id=str(task_id))
        )

    @router.post("/tasks/{task_id}/transitions", response_model=Task, status_code=200)
    async def transition_task(
        data: Transition,
        request: Request,
        response: Response,
        task_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response, await service.atransition_task(principal=principal, data=data, **headers, task_id=str(task_id))
        )

    @router.post("/tasks/{task_id}/comments", response_model=Comment, status_code=201)
    async def add_comment_task(
        data: CommentCreate,
        request: Request,
        response: Response,
        task_id: UUID,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        headers.pop("version", None)
        return _etag(
            response, await service.aadd_comment_task(principal=principal, data=data, **headers, task_id=str(task_id))
        )

    @router.get("/tasks/{task_id}/comments", response_model=Page[Comment])
    async def list_task_comments(
        task_id: UUID, query: ListQuery = Depends(), principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return await service.alist_comments(principal=principal, kind="task", record_id=str(task_id), query=query)

    @router.get("/activity", response_model=Page[Activity])
    async def activity(query: ListQuery = Depends(), principal: Principal = Depends(principal_from_request)) -> Any:
        return await service.alist_activity(principal=principal, query=query)

    @router.get("/products/{product_id}/members", response_model=Page[Membership])
    async def members(
        product_id: UUID, query: ListQuery = Depends(), principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return await service.alist_members(principal=principal, product_id=str(product_id), query=query)

    @router.post("/products/{product_id}/members", response_model=Membership, status_code=201)
    async def add_member(
        product_id: UUID,
        data: MemberCreate,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response, await service.aadd_member(principal=principal, product_id=str(product_id), data=data, **headers)
        )

    @router.patch("/products/{product_id}/members/{member_id}", response_model=Membership)
    async def update_member(
        product_id: UUID,
        member_id: str,
        data: MemberPatch,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.aupdate_member(
                principal=principal, product_id=str(product_id), member_id=member_id, data=data, **headers
            ),
        )

    @router.post("/tasks/{task_id}/archive", response_model=Task)
    async def archive_task(
        task_id: UUID,
        data: Reason,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response, await service.aarchive_task(task_id=str(task_id), data=data, principal=principal, **headers)
        )

    @router.post("/tasks/{task_id}/restore", response_model=Task)
    async def restore_task(
        task_id: UUID,
        data: Reason,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response, await service.arestore_task(task_id=str(task_id), data=data, principal=principal, **headers)
        )

    @router.post("/projects/{project_id}/archive", response_model=Project)
    async def archive_project(
        project_id: UUID,
        data: Reason,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.aarchive_project(project_id=str(project_id), data=data, principal=principal, **headers),
        )

    @router.post("/projects/{project_id}/restore", response_model=Project)
    async def restore_project(
        project_id: UUID,
        data: Reason,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.arestore_project(project_id=str(project_id), data=data, principal=principal, **headers),
        )

    @router.post("/tasks/{task_id}/runs", status_code=202)
    async def run_task(
        task_id: UUID,
        data: RunTask,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        if headers["version"] is None:
            raise CompanyError(428, "precondition_required", "If-Match is required")
        headers.pop("request_id")
        return await service.arun_task(task_id=str(task_id), principal=principal, message=data.message, **headers)

    @router.get("/tasks/{task_id}/runs")
    async def list_runs(task_id: UUID, principal: Principal = Depends(principal_from_request)) -> Any:
        return await service.alist_runs(task_id=str(task_id), principal=principal)

    @router.post("/tasks/{task_id}/runs/{run_id}/cancel")
    async def cancel_run(task_id: UUID, run_id: UUID, principal: Principal = Depends(principal_from_request)) -> Any:
        return await service.acancel_task_run(task_id=str(task_id), run_id=str(run_id), principal=principal)

    @router.post("/projects/{project_id}/summary", response_model=Project)
    async def update_summary(
        project_id: UUID,
        data: ProjectSummary,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.aupdate_project_summary(
                project_id=str(project_id), principal=principal, data=data, **headers
            ),
        )

    @router.put("/tasks/{task_id}/schedule", response_model=Task)
    async def set_schedule(
        task_id: UUID,
        data: TaskSchedule,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response, await service.aset_schedule(task_id=str(task_id), principal=principal, data=data, **headers)
        )

    @router.get("/tasks/{task_id}/runs/{run_id}")
    async def get_task_result(
        task_id: UUID, run_id: UUID, principal: Principal = Depends(principal_from_request)
    ) -> Any:
        return await service.aget_task_result(task_id=str(task_id), run_id=str(run_id), principal=principal)

    @router.put("/tasks/{task_id}/review/pull-request", response_model=Task)
    async def set_review_pull_request(
        task_id: UUID,
        data: PullRequestReview,
        response: Response,
        headers: dict = Depends(mutation_headers),
        principal: Principal = Depends(principal_from_request),
    ) -> Any:
        return _etag(
            response,
            await service.aset_review_pull_request(task_id=str(task_id), data=data, principal=principal, **headers),
        )

    return router
