"""Trusted server context and Product policy, shared by HTTP and direct service calls."""

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from agno.os.authz.provider import AuthorizationContext, AuthorizationProvider


@dataclass(frozen=True)
class Principal:
    """Construct only at a verified server boundary, never from business request data."""

    id: str
    provider: AuthorizationProvider
    scopes: Tuple[str, ...] = ()
    claims: Mapping[str, Any] = field(default_factory=dict)

    agent_id: Optional[str] = None
    product_id: Optional[str] = None

    def context(self, action: str, product_id: Optional[str] = None) -> AuthorizationContext:
        return AuthorizationContext(
            principal_id=self.id,
            scopes=list(self.scopes),
            claims=dict(self.claims),
            resource_type="company" if action == "bootstrap" else "company_products",
            resource_id=product_id,
            action="manage" if action == "bootstrap" else action,
            admin_scope="company:manage",
        )

    async def acontext(self, action: str, product_id: Optional[str] = None) -> AuthorizationContext:
        return self.context(action, product_id)


class CompanyError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)
