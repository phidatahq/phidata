"""Tenant-scoped registry listing: one code-defined Registry, per-tenant visibility."""

from datetime import UTC, datetime, timedelta
from typing import List, Optional

import jwt
import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.os import AgentOS, Authorization
from agno.os.tenancy import TenantEntitlements, is_entitled
from agno.registry import Registry

JWT_SECRET = "test-secret-key-at-least-256-bits-long-000"
OS_ID = "tenant-registry-test-os"


def search(query: str) -> str:
    """Search the web."""
    return query


def sql(query: str) -> str:
    """Run a SQL query."""
    return query


def slack(message: str) -> str:
    """Post to Slack."""
    return message


def _token(scopes: List[str], org_id: Optional[str] = None, sub: str = "user") -> str:
    payload = {"sub": sub, "aud": OS_ID, "scopes": scopes, "exp": datetime.now(UTC) + timedelta(hours=1)}
    if org_id is not None:
        payload["org_id"] = org_id
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _client(tenant_claim: Optional[str] = "org_id", tenant_entitlements: Optional[TenantEntitlements] = None):
    agent_os = AgentOS(
        id=OS_ID,
        agents=[Agent(id="support-agent", name="Support Agent")],
        registry=Registry(tools=[search, sql, slack]),
        authorization=Authorization(
            verification_keys=[JWT_SECRET], algorithm="HS256", verify_audience=True, audience=OS_ID
        ),
        tenant_claim=tenant_claim,
        tenant_entitlements=tenant_entitlements,
        telemetry=False,
    )
    return TestClient(agent_os.get_app())


def _list_tools(client: TestClient, token: str):
    return client.get("/registry", params={"resource_type": "tool"}, headers={"Authorization": f"Bearer {token}"})


def _tool_names(client: TestClient, token: str) -> List[str]:
    response = _list_tools(client, token)
    assert response.status_code == 200, response.text
    return sorted(item["name"] for item in response.json()["data"])


class TestRegistryListing:
    def test_without_a_tenant_claim_the_listing_is_unfiltered(self):
        client = _client(tenant_claim=None)
        assert _tool_names(client, _token(["registry:read"], org_id="acme")) == ["search", "slack", "sql"]

    def test_each_tenant_sees_only_its_entitled_entries(self):
        client = _client(
            tenant_entitlements=TenantEntitlements(
                {"acme": {"tool": ["search", "sql"]}, "globex": {"tool": ["search"]}}
            )
        )
        assert _tool_names(client, _token(["registry:read"], org_id="acme")) == ["search", "sql"]
        assert _tool_names(client, _token(["registry:read"], org_id="globex")) == ["search"]

    def test_the_wildcard_grants_every_entry_of_a_type(self):
        client = _client(tenant_entitlements=TenantEntitlements({"acme": {"tool": ["*"]}}))
        assert _tool_names(client, _token(["registry:read"], org_id="acme")) == ["search", "slack", "sql"]

    def test_a_tenant_with_no_entitlements_sees_nothing(self):
        client = _client()
        assert _tool_names(client, _token(["registry:read"], org_id="unknown")) == []

    def test_the_total_count_does_not_reveal_hidden_entries(self):
        client = _client(tenant_entitlements=TenantEntitlements({"globex": {"tool": ["search"]}}))
        response = _list_tools(client, _token(["registry:read"], org_id="globex"))
        assert response.json()["meta"]["total_count"] == 1

    def test_a_token_without_the_tenant_claim_is_refused(self):
        client = _client(tenant_entitlements=TenantEntitlements({"acme": {"tool": ["*"]}}))
        response = _list_tools(client, _token(["registry:read"]))
        assert response.status_code == 403
        assert "org_id" in response.json()["detail"]

    def test_an_admin_sees_the_whole_registry(self):
        client = _client()
        assert _tool_names(client, _token(["agent_os:admin"])) == ["search", "slack", "sql"]


class TestEntitlementRoutes:
    def test_an_entitlement_change_applies_to_the_next_listing(self):
        client = _client()
        admin = {"Authorization": f"Bearer {_token(['agent_os:admin'])}"}
        tenant_token = _token(["registry:read"], org_id="globex")
        assert _tool_names(client, tenant_token) == []

        response = client.put("/tenants/globex/entitlements", headers=admin, json={"tool": ["search", "sql"]})
        assert response.status_code == 200
        assert response.json() == {"tenant_id": "globex", "entitlements": {"tool": ["search", "sql"]}}
        assert _tool_names(client, tenant_token) == ["search", "sql"]

        assert client.get("/tenants/globex/entitlements", headers=admin).json()["entitlements"] == {
            "tool": ["search", "sql"]
        }

    def test_a_tenant_cannot_entitle_itself(self):
        client = _client()
        headers = {"Authorization": f"Bearer {_token(['registry:read'], org_id='globex')}"}
        response = client.put("/tenants/globex/entitlements", headers=headers, json={"tool": ["*"]})
        assert response.status_code == 403
        assert client.get("/tenants/globex/entitlements", headers=headers).status_code == 403

    def test_the_write_scope_is_enough_to_entitle(self):
        client = _client()
        headers = {"Authorization": f"Bearer {_token(['tenants:write'])}"}
        assert client.put("/tenants/acme/entitlements", headers=headers, json={"tool": ["search"]}).status_code == 200

    def test_an_unknown_resource_type_is_rejected(self):
        client = _client()
        headers = {"Authorization": f"Bearer {_token(['agent_os:admin'])}"}
        assert client.put("/tenants/acme/entitlements", headers=headers, json={"gadget": ["x"]}).status_code == 422

    def test_the_routes_are_not_served_without_a_tenant_claim(self):
        client = _client(tenant_claim=None)
        headers = {"Authorization": f"Bearer {_token(['agent_os:admin'])}"}
        assert client.get("/tenants/acme/entitlements", headers=headers).status_code == 404


class TestTenantEntitlements:
    def test_entitlements_without_a_tenant_claim_are_refused(self):
        with pytest.raises(ValueError, match="tenant_claim"):
            _client(tenant_claim=None, tenant_entitlements=TenantEntitlements())

    def test_an_unknown_resource_type_is_refused(self):
        with pytest.raises(ValueError, match="gadget"):
            TenantEntitlements({"acme": {"gadget": ["x"]}})

    def test_set_replaces_the_previous_entitlements(self):
        store = TenantEntitlements({"acme": {"tool": ["search"], "model": ["*"]}})
        store.set("acme", {"tool": ["sql"]})
        assert store.get("acme") == {"tool": ["sql"]}

    def test_get_returns_a_copy(self):
        store = TenantEntitlements({"acme": {"tool": ["search"]}})
        store.get("acme")["tool"].append("sql")
        assert store.get("acme") == {"tool": ["search"]}

    @pytest.mark.asyncio
    async def test_the_async_variants_match_the_sync_ones(self):
        store = TenantEntitlements()
        await store.aset("acme", {"tool": ["search"]})
        assert await store.aget("acme") == store.get("acme") == {"tool": ["search"]}

    def test_an_entry_is_matched_by_name_or_id(self):
        entitlements = {"agent": ["support-agent"]}
        assert is_entitled(entitlements, "agent", "Support Agent", "support-agent")
        assert not is_entitled(entitlements, "agent", "Other Agent", "other-agent")
        assert not is_entitled(entitlements, "tool", "support-agent")
