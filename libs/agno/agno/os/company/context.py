"""Trusted Company execution context; never populated from model arguments."""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Optional

from agno.os.company.policy import Principal


@dataclass(frozen=True)
class CompanyContext:
    service: Any
    principal: Principal
    product_id: Optional[str] = None


current_company: ContextVar[Optional[CompanyContext]] = ContextVar("current_company", default=None)


class CompanyContextMiddleware:
    """Installed inside authentication so inline Team delegation inherits verified identity."""

    def __init__(self, app: Any, service: Any):
        self.app, self.service = app, service

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        from fastapi import Request

        from agno.os.company.policy import CompanyError
        from agno.os.company.router import principal_from_request

        context = None
        if scope["type"] == "http":
            try:
                context = CompanyContext(self.service, principal_from_request(Request(scope)))
            except CompanyError:
                pass
        token = current_company.set(context)
        try:
            await self.app(scope, receive, send)
        finally:
            current_company.reset(token)
