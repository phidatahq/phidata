"""Require operator authority before exposing the manager's platform capabilities."""

from dataclasses import replace
from typing import Any, List, Set, Tuple

from agno.os.authz.provider import AuthorizationContext, AuthorizationProvider


class ManagerAuthorizationProvider(AuthorizationProvider):
    """Keep ordinary component grants from granting platform administration.

    The underlying provider decides what admin means, including managed roles
    and custom providers. Token scopes alone are never substituted for its policy.
    Read access and unrelated components keep their existing permissions.
    """

    def __init__(self, provider: AuthorizationProvider, components: Set[Tuple[str, str]]):
        self.provider = provider
        self.components = components
        self.enforces_token_scopes = provider.enforces_token_scopes

    def _requires_admin(self, ctx: AuthorizationContext) -> bool:
        return (ctx.resource_type, ctx.resource_id) in self.components and ctx.action != "read"

    @staticmethod
    def _admin_context(ctx: AuthorizationContext) -> AuthorizationContext:
        return replace(ctx, resource_type=None, resource_id=None, action=None)

    def check(self, ctx: AuthorizationContext) -> bool:
        if self._requires_admin(ctx) and not self.provider.authorize_route(
            self._admin_context(ctx), [ctx.admin_scope or "agent_os:admin"]
        ):
            return False
        return self.provider.check(ctx)

    async def acheck(self, ctx: AuthorizationContext) -> bool:
        if self._requires_admin(ctx) and not await self.provider.aauthorize_route(
            self._admin_context(ctx), [ctx.admin_scope or "agent_os:admin"]
        ):
            return False
        return await self.provider.acheck(ctx)

    def authorize_route(self, ctx: AuthorizationContext, required_scopes: List[str]) -> bool:
        if self._requires_admin(ctx) and not self.provider.authorize_route(
            self._admin_context(ctx), [ctx.admin_scope or "agent_os:admin"]
        ):
            return False
        return self.provider.authorize_route(ctx, required_scopes)

    async def aauthorize_route(self, ctx: AuthorizationContext, required_scopes: List[str]) -> bool:
        if self._requires_admin(ctx) and not await self.provider.aauthorize_route(
            self._admin_context(ctx), [ctx.admin_scope or "agent_os:admin"]
        ):
            return False
        return await self.provider.aauthorize_route(ctx, required_scopes)

    def accessible_resource_ids(self, ctx: AuthorizationContext) -> Set[str]:
        return self.provider.accessible_resource_ids(ctx)

    async def aaccessible_resource_ids(self, ctx: AuthorizationContext) -> Set[str]:
        return await self.provider.aaccessible_resource_ids(ctx)

    def filter_accessible(self, ctx: AuthorizationContext, resources: List[Any]) -> List[Any]:
        return self.provider.filter_accessible(ctx, resources)

    async def afilter_accessible(self, ctx: AuthorizationContext, resources: List[Any]) -> List[Any]:
        return await self.provider.afilter_accessible(ctx, resources)
