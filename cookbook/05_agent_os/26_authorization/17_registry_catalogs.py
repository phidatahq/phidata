"""
Registry catalogs - named sets of registry entries, built over the API.

(Read 16_tenant_registry.py first. It scopes the registry with one role per tenant.)

In 16 a tenant's view of the registry is the scopes on its role. That stops
working when two tenants should share a view, or one tenant needs several.
A catalog is that view as its own stored object:

  - Registry(tools=[...])           the global registry. One, in code.
  - PUT /authz/catalogs/{slug}      a catalog: a name plus a list of registry
                                    entries, each {"type": "tool", "name": "sql"}.
                                    Stored in your database, built at runtime.
  - catalogs:<slug>:read            the scope that grants a catalog. A role points
                                    at catalogs through its scopes, so one role can
                                    hold several and several roles can share one.

GET /registry lists the entries of every catalog the caller holds, and
GET /registry?catalog=<slug> lists one. The authorization provider still
decides which catalogs a caller holds, so this is the same RBAC as every other
route, with the catalog as the thing being granted.

Run it:
    pip install "agno[os]"
    python 17_registry_catalogs.py
(no extra services and no model key needed; roles and catalogs live in SQLite under tmp/.)
"""

import os
from datetime import UTC, datetime, timedelta
from typing import List, Optional

import jwt
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, Authorization
from agno.registry import Registry

JWT_SECRET = os.getenv("JWT_VERIFICATION_KEY", "your-secret-key-at-least-256-bits-long")
OS_ID = "registry-catalogs-os"

os.makedirs("tmp", exist_ok=True)
if os.path.exists("tmp/registry_catalogs.db"):
    os.remove("tmp/registry_catalogs.db")

db = SqliteDb(db_file="tmp/registry_catalogs.db")


# ---------------------------------------------------------------------------
# The global registry: defined in code, deployed once.
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


registry = Registry(name="Global Registry", tools=[search, sql, slack])


# ---------------------------------------------------------------------------
# Tenants are roles. A role's scopes name the catalogs it holds.
# ---------------------------------------------------------------------------

authz = Authorization(
    db=db,
    verification_keys=[JWT_SECRET],
    algorithm="HS256",
    verify_audience=True,
    audience=OS_ID,
    roles_claim="org_id",  # <- the tenant claim your IdP sends
    # Operators are authorized by the scopes on their own token, tenants by their role.
    trust_token_scopes=True,
)
authz.define_role("acme", ["catalogs:starter:read", "catalogs:analytics:read"])
authz.define_role("globex", ["catalogs:starter:read"])

# AgentOS needs something to serve; the agent itself is never run here.
support_agent = Agent(
    id="support-agent",
    name="Support Agent",
    model=OpenAIResponses(id="gpt-5.6-luna"),
    db=db,
)

agent_os = AgentOS(
    id=OS_ID,
    description="AgentOS with registry catalogs",
    agents=[support_agent],
    db=db,
    registry=registry,
    authorization=authz,
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

    def token(
        sub: str, org_id: Optional[str] = None, scopes: Optional[List[str]] = None
    ) -> str:
        """A token the way an IdP would mint it: identity plus the person's tenant."""
        claims = {
            "sub": sub,
            "aud": OS_ID,
            "scopes": scopes or [],  # tenants carry no agno scopes; the ROLE decides
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        if org_id is not None:
            claims["org_id"] = org_id
        return jwt.encode(claims, JWT_SECRET, algorithm="HS256")

    operator = {
        "Authorization": f"Bearer {token('operator', scopes=['agent_os:admin'])}"
    }
    acme = token("alice", "acme")
    globex = token("bob", "globex")

    def set_catalog(slug: str, tools: List[str]) -> int:
        r = client.put(
            f"/authz/catalogs/{slug}",
            headers=operator,
            json={"entries": [{"type": "tool", "name": name} for name in tools]},
        )
        return r.status_code

    def show_tools(label: str, tok: str, catalog: Optional[str] = None) -> None:
        params = {"resource_type": "tool"}
        if catalog is not None:
            params["catalog"] = catalog
        r = client.get(
            "/registry", params=params, headers={"Authorization": f"Bearer {tok}"}
        )
        if r.status_code != 200:
            print(f"  {label:36s} -> BLOCKED ({r.status_code})")
            return
        names = ", ".join(item["name"] for item in r.json()["data"]) or "(nothing)"
        print(f"  {label:36s} -> {names}")

    print("\n" + "=" * 80)
    print("REGISTRY CATALOGS - named sets of registry entries, built over the API")
    print("=" * 80)
    print("  global registry in code: search, sql, slack")
    print("  roles: acme holds starter + analytics | globex holds starter\n")

    print("1. no catalog exists yet, so the roles grant nothing")
    show_tools("acme user", acme)

    print("\n2. the operator builds two catalogs over the API (no deploy)")
    print(
        f"  PUT /authz/catalogs/starter          -> {set_catalog('starter', ['search'])}"
    )
    print(
        f"  PUT /authz/catalogs/analytics        -> {set_catalog('analytics', ['sql'])}"
    )

    print("\n3. GET /registry lists every catalog the caller holds")
    show_tools("acme user   (starter + analytics)", acme)
    show_tools("globex user (starter)", globex)

    print("\n4. GET /registry?catalog=... lists one catalog")
    show_tools("acme user,   catalog=analytics", acme, catalog="analytics")
    show_tools("globex user, catalog=analytics", globex, catalog="analytics")

    print("\n5. starter is shared: one write changes it for both tenants")
    print(
        f"  PUT /authz/catalogs/starter          -> {set_catalog('starter', ['search', 'slack'])}"
    )
    show_tools("acme user   (starter + analytics)", acme)
    show_tools("globex user (starter)", globex)

    print("\n6. a tenant cannot build or change a catalog")
    r = client.put(
        "/authz/catalogs/starter",
        headers={"Authorization": f"Bearer {globex}"},
        json={"entries": [{"type": "tool", "name": "sql"}]},
    )
    print(f"  globex user PUT /authz/catalogs/starter -> {r.status_code}")

    print("=" * 80)
    print(
        "the point: the registry stays one object in code. A catalog is a stored, named"
    )
    print("view of it, and the existing RBAC decides which catalogs each caller holds.")
    print("=" * 80)
