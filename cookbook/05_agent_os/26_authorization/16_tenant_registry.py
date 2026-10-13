"""
Tenant-scoped registry - one catalog in code, per-tenant visibility as data.

(New to authorization? Read 01_managed_roles.py first.)

A Registry holds live Python objects (tool callables, model clients, database
connections), so it is defined in code and deployed once. Which of its entries
a tenant may SEE is a different kind of thing: it changes when a customer is
onboarded or upgraded, and that should not need a deploy.

This example keeps the two apart:

  - Registry(tools=[...])            the catalog. One, global, in code.
  - tenant_claim="org_id"            the tenant is read from the caller's JWT, so
                                     the user-to-tenant mapping stays in your IdP.
  - PUT /tenants/{id}/entitlements   which catalog entries a tenant may see.
                                     Data, edited over the API at runtime.

GET /registry is the same endpoint for everyone and answers differently per
tenant. A token with no tenant claim is refused rather than shown everything,
and a tenant with no entitlements sees nothing.

Entitlements here are held in memory: they are lost on restart and are not
shared between workers.

Run it:
    pip install "agno[os]"
    python 16_tenant_registry.py
(no extra services, no database and no model key needed.)
"""

import os
from datetime import UTC, datetime, timedelta
from typing import List, Optional

import jwt
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, Authorization
from agno.registry import Registry

JWT_SECRET = os.getenv("JWT_VERIFICATION_KEY", "your-secret-key-at-least-256-bits-long")
OS_ID = "tenant-registry-os"


# ---------------------------------------------------------------------------
# The catalog: defined in code, deployed once, shared by every tenant.
# ---------------------------------------------------------------------------


def search(query: str) -> str:
    """Search the public web."""
    return f"results for {query}"


def sql(query: str) -> str:
    """Run a read-only SQL query against the warehouse."""
    return f"rows for {query}"


def slack(channel: str, message: str) -> str:
    """Post a message to a Slack channel."""
    return f"posted to {channel}"


registry = Registry(name="Catalog", tools=[search, sql, slack])

# AgentOS needs something to serve; the agent itself is never run here.
support_agent = Agent(
    id="support-agent",
    name="Support Agent",
    model=OpenAIResponses(id="gpt-5.6-luna"),
)


# ---------------------------------------------------------------------------
# Wire it in: name the JWT claim that carries the tenant.
# ---------------------------------------------------------------------------

agent_os = AgentOS(
    id=OS_ID,
    description="AgentOS with a tenant-scoped registry",
    agents=[support_agent],
    registry=registry,
    authorization=Authorization(
        verification_keys=[JWT_SECRET],
        algorithm="HS256",
        verify_audience=True,
        audience=OS_ID,
    ),
    # The tenant comes from the token. AgentOS never stores who belongs to which tenant.
    tenant_claim="org_id",
)
app = agent_os.get_app()


# ---------------------------------------------------------------------------
# Run Example
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging

    from fastapi.testclient import TestClient

    logging.disable(logging.CRITICAL)
    client = TestClient(app)

    def token(sub: str, scopes: List[str], org_id: Optional[str] = None) -> str:
        payload = {
            "sub": sub,
            "aud": OS_ID,
            "scopes": scopes,
            "exp": datetime.now(UTC) + timedelta(hours=24),
        }
        if org_id is not None:
            payload["org_id"] = org_id  # the tenant claim your IdP sends
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    operator = token("operator", ["agent_os:admin"])
    acme_user = token("alice", ["registry:read"], org_id="acme")
    globex_user = token("bob", ["registry:read"], org_id="globex")
    no_tenant_user = token("carol", ["registry:read"])

    def entitle(tok: str, tenant_id: str, tools: List[str]) -> int:
        r = client.put(
            f"/tenants/{tenant_id}/entitlements",
            headers={"Authorization": f"Bearer {tok}"},
            json={"tool": tools},
        )
        return r.status_code

    def show_tools(label: str, tok: str) -> None:
        r = client.get(
            "/registry",
            params={"resource_type": "tool"},
            headers={"Authorization": f"Bearer {tok}"},
        )
        if r.status_code != 200:
            print(f"  {label:34s} -> BLOCKED ({r.status_code})")
            return
        names = ", ".join(item["name"] for item in r.json()["data"]) or "(nothing)"
        print(f"  {label:34s} -> {names}")

    print("\n" + "=" * 80)
    print("TENANT REGISTRY - one catalog, a different view per tenant")
    print("=" * 80)
    print("  catalog in code: search, sql, slack\n")

    print("1. before any entitlement exists")
    show_tools("operator (admin scope)", operator)
    show_tools("acme user", acme_user)

    print("\n2. the operator entitles each tenant over the API (no deploy)")
    print(
        f"  PUT /tenants/acme/entitlements     -> {entitle(operator, 'acme', ['search', 'sql', 'slack'])}"
    )
    print(
        f"  PUT /tenants/globex/entitlements   -> {entitle(operator, 'globex', ['search'])}"
    )

    print("\n3. the same GET /registry, answered per tenant")
    show_tools("acme user   (org_id=acme)", acme_user)
    show_tools("globex user (org_id=globex)", globex_user)
    show_tools("user with no org_id claim", no_tenant_user)

    print("\n4. a tenant cannot entitle itself")
    print(
        f"  globex user PUT own entitlements   -> {entitle(globex_user, 'globex', ['*'])}"
    )

    print("\n5. globex upgrades: the operator adds sql, effective on the next request")
    print(
        f"  PUT /tenants/globex/entitlements   -> {entitle(operator, 'globex', ['search', 'sql'])}"
    )
    show_tools("globex user (org_id=globex)", globex_user)

    print("=" * 80)
    print("the point: the catalog stays one object in code. Who sees which entry is")
    print("data keyed by the JWT tenant claim, changed over the API with no deploy.")
    print("=" * 80)
