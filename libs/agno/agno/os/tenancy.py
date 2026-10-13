"""Per-tenant visibility of the code-defined registry.

One Registry describes what a deployment can do. Which of its entries a tenant
may see is data: a tenant id maps to the registry entry names that tenant is
entitled to, per resource type. The tenant id is read from a claim on the
caller's verified JWT (``AgentOS(tenant_claim="org_id")``), so the mapping of
users to tenants stays in the identity provider.

    from agno.os import AgentOS
    from agno.os.tenancy import TenantEntitlements

    agent_os = AgentOS(
        registry=Registry(tools=[search, sql]),
        authorization=Authorization(...),
        tenant_claim="org_id",
        tenant_entitlements=TenantEntitlements({"acme": {"tool": ["*"]}}),
    )

    GET /registry                         filtered to the caller's tenant
    GET /tenants/{tenant_id}/entitlements what a tenant may see
    PUT /tenants/{tenant_id}/entitlements replace what a tenant may see

Proof of concept: entitlements live in this process. They do not survive a
restart and are not shared between workers.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from agno.os.auth import caller_scopes_are_authoritative, get_authentication_dependency
from agno.os.schema import RegistryResourceType, UnauthenticatedResponse
from agno.os.scopes import AgentOSScope
from agno.os.settings import AgnoAPISettings

# Entitles a tenant to every entry of a resource type.
ALL_ENTRIES = "*"


def is_entitled(entitlements: Dict[str, List[str]], resource_type: str, name: str, id: Optional[str] = None) -> bool:
    """Whether ``entitlements`` grant a registry entry, matched by name or id.

    A resource type with no list grants nothing, so a tenant sees only what it
    was explicitly given.
    """
    allowed = entitlements.get(resource_type) or []
    return ALL_ENTRIES in allowed or name in allowed or (id is not None and id in allowed)


class TenantEntitlements:
    """In-memory map of tenant id to the registry entries that tenant may see.

    Entitlements are keyed by registry resource type ("tool", "model", ...) and
    list entry names or ids; ``"*"`` grants every entry of that type.
    """

    def __init__(self, entitlements: Optional[Dict[str, Dict[str, List[str]]]] = None):
        self._entitlements: Dict[str, Dict[str, List[str]]] = {}
        for tenant_id, tenant_entitlements in (entitlements or {}).items():
            self.set(tenant_id, tenant_entitlements)

    def get(self, tenant_id: str) -> Dict[str, List[str]]:
        """The entitlements of ``tenant_id``; empty for a tenant never given any."""
        return {resource_type: list(names) for resource_type, names in self._entitlements.get(tenant_id, {}).items()}

    def set(self, tenant_id: str, entitlements: Dict[str, List[str]]) -> None:
        """Replace the entitlements of ``tenant_id``."""
        valid_types = {resource_type.value for resource_type in RegistryResourceType}
        normalized: Dict[str, List[str]] = {}
        for resource_type, names in entitlements.items():
            key = resource_type.value if isinstance(resource_type, RegistryResourceType) else resource_type
            if key not in valid_types:
                raise ValueError(f"Unknown registry resource type '{key}'. Expected one of: {sorted(valid_types)}")
            normalized[key] = list(names)
        self._entitlements[tenant_id] = normalized

    async def aget(self, tenant_id: str) -> Dict[str, List[str]]:
        return self.get(tenant_id)

    async def aset(self, tenant_id: str, entitlements: Dict[str, List[str]]) -> None:
        self.set(tenant_id, entitlements)


def resolve_registry_tenant(request: Request, tenant_claim: str) -> Optional[str]:
    """The tenant a registry listing is filtered to, or None for an unscoped caller.

    Unscoped callers see the whole registry: the security key, the internal
    scheduler, and a caller whose token scopes carry the admin scope. Every
    other caller must present the tenant claim; one without it is refused
    rather than shown an unfiltered listing.
    """
    state = request.state
    if getattr(state, "security_key_verified", False) or getattr(state, "is_internal_service", False):
        return None

    admin_scope = getattr(state, "admin_scope", None) or AgentOSScope.ADMIN.value
    scopes = getattr(state, "scopes", None) or []
    if admin_scope in scopes and caller_scopes_are_authoritative(request):
        return None

    claims: Dict[str, Any] = getattr(state, "claims", None) or {}
    tenant_id = claims.get(tenant_claim)
    if not isinstance(tenant_id, str) or not tenant_id:
        raise HTTPException(
            status_code=403,
            detail=f"This AgentOS scopes the registry by tenant: the token must carry a '{tenant_claim}' claim.",
        )
    return tenant_id


class TenantEntitlementsResponse(BaseModel):
    tenant_id: str
    entitlements: Dict[str, List[str]] = Field(
        ..., description="Registry entry names or ids the tenant may see, per resource type. '*' grants all."
    )


def get_tenant_router(
    tenant_entitlements: TenantEntitlements, settings: AgnoAPISettings = AgnoAPISettings()
) -> APIRouter:
    router = APIRouter(
        dependencies=[Depends(get_authentication_dependency(settings))],
        tags=["Tenants"],
        responses={401: {"description": "Unauthorized", "model": UnauthenticatedResponse}},
    )

    @router.get(
        "/tenants/{tenant_id}/entitlements",
        response_model=TenantEntitlementsResponse,
        status_code=200,
        operation_id="get_tenant_entitlements",
        summary="Get Tenant Entitlements",
        description="The registry entries a tenant may see, per resource type.",
    )
    async def get_tenant_entitlements(tenant_id: str) -> TenantEntitlementsResponse:
        return TenantEntitlementsResponse(tenant_id=tenant_id, entitlements=await tenant_entitlements.aget(tenant_id))

    @router.put(
        "/tenants/{tenant_id}/entitlements",
        response_model=TenantEntitlementsResponse,
        status_code=200,
        operation_id="set_tenant_entitlements",
        summary="Set Tenant Entitlements",
        description="Replace the registry entries a tenant may see. Resource types left out grant nothing.",
    )
    async def set_tenant_entitlements(
        tenant_id: str, entitlements: Dict[RegistryResourceType, List[str]]
    ) -> TenantEntitlementsResponse:
        await tenant_entitlements.aset(
            tenant_id, {resource_type.value: names for resource_type, names in entitlements.items()}
        )
        return TenantEntitlementsResponse(tenant_id=tenant_id, entitlements=await tenant_entitlements.aget(tenant_id))

    return router
