"""Product writes resolve per-record grants: products:<id|own|*>:<action>, with bare scopes unchanged."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.company import Product
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, CompanyConfig
from agno.os.config import AuthorizationConfig
from agno.os.scopes import ResourceGrant, get_resource_grant

SECRET = "company-resource-scopes-secret-at-least-32-bytes"
READ = ["products:read", "routines:read"]


@pytest.fixture
def system(tmp_path, request):
    isolation = request.param
    db = SqliteDb(db_file=str(tmp_path / "scopes.db"))
    agent_os = AgentOS(
        id="scopes",
        db=db,
        agents=[Agent(id="reader", telemetry=False)],
        company=CompanyConfig(products=[Product(id="research", name="Research")]),
        telemetry=False,
        authorization=True,
        authorization_config=AuthorizationConfig(
            verification_keys=[SECRET], algorithm="HS256", user_isolation=isolation
        ),
    )
    with TestClient(agent_os.get_app()) as client:
        yield client
    db.close()


def headers(user, *scopes):
    claims = {
        "sub": user,
        "aud": "scopes",
        "scopes": [*READ, *scopes],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return {"Authorization": "Bearer " + jwt.encode(claims, SECRET, algorithm="HS256")}


def rename(client, product_id, caller):
    response = client.patch("/company/products/" + product_id, headers=caller, json={"purpose": "edited"})
    if response.status_code == 200:
        assert response.json()["purpose"] == "edited" and response.json()["updated_at"] is not None
    return response.status_code


def alice_product(client):
    response = client.post("/company/products", headers=headers("alice", "products:write"), json={"name": "Alice's"})
    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == "alice"
    return response.json()["id"]


def test_grant_resolution():
    assert get_resource_grant(["products:write"], "products", "write") == ResourceGrant(all=True)
    assert get_resource_grant(["products:write"], "products", "write", user_isolation=True) == ResourceGrant(own=True)
    assert get_resource_grant(["products:*:write"], "products", "write", user_isolation=True) == ResourceGrant(all=True)
    assert get_resource_grant(["products:own:write"], "products", "write") == ResourceGrant(own=True)
    assert get_resource_grant(["products:a:write", "products:b:write"], "products", "write").ids == {"a", "b"}
    assert get_resource_grant(["products:a:read"], "products", "write") == ResourceGrant()
    assert get_resource_grant(["agent_os:admin"], "products", "write", user_isolation=True) == ResourceGrant(all=True)
    own = ResourceGrant(own=True)
    assert own.allows("p", "alice", "alice")
    assert not own.allows("p", "alice", "bob")
    assert not own.allows("p", None, "bob")
    assert not own.allows("p", None, None)


@pytest.mark.parametrize("system", [True], indirect=True)
def test_bare_scopes_under_isolation_keep_todays_owner_rule(system):
    client = system
    product_id = alice_product(client)
    assert rename(client, product_id, headers("alice", "products:write")) == 200
    assert rename(client, product_id, headers("bob", "products:write")) == 403
    assert rename(client, "research", headers("bob", "products:write")) == 403
    assert rename(client, "research", headers("root", "agent_os:admin")) == 200


@pytest.mark.parametrize("system", [False], indirect=True)
def test_bare_scopes_without_isolation_keep_todays_open_writes(system):
    client = system
    product_id = alice_product(client)
    assert rename(client, product_id, headers("bob", "products:write")) == 200
    assert rename(client, "research", headers("bob", "products:write")) == 200


@pytest.mark.parametrize("system", [False, True], indirect=True)
def test_per_product_scope_grants_one_declared_product(system):
    client = system
    product_id = alice_product(client)
    bob = headers("bob", "products:research:write")
    assert rename(client, "research", bob) == 200
    assert rename(client, product_id, bob) == 403
    # The same grant lets Bob add a Routine to the declared Product.
    routine = dict(product_id="research", name="intake", template="intake", executor_type="agent", executor_id="reader")
    routine_headers = headers(
        "bob", "products:research:write", "routines:write", "schedules:write", "agents:reader:run"
    )
    created = client.post("/company/routines", headers=routine_headers, json=routine)
    assert created.status_code == 201, created.text
    assert created.json()["user_id"] == "bob"
    # Write does not imply delete.
    assert client.delete("/company/products/research", headers=bob).status_code == 403
    deleted = client.delete("/company/products/research", headers=headers("bob", "products:research:delete"))
    assert deleted.status_code == 204, deleted.text
    assert client.get("/company/products/research", params={"include_deleted": True}, headers=bob).json()["deleted_at"]


@pytest.mark.parametrize("system", [False, True], indirect=True)
def test_own_scope_is_owner_only_with_or_without_isolation(system):
    client = system
    product_id = alice_product(client)
    assert rename(client, product_id, headers("alice", "products:own:write")) == 200
    assert rename(client, product_id, headers("bob", "products:own:write")) == 403
    assert rename(client, "research", headers("bob", "products:own:write")) == 403
    created = client.post("/company/products", headers=headers("bob", "products:own:write"), json={"name": "Bob's"})
    assert created.status_code == 201 and created.json()["user_id"] == "bob"


@pytest.mark.parametrize("system", [True], indirect=True)
def test_wildcard_scope_opts_out_of_isolation_for_products(system):
    client = system
    product_id = alice_product(client)
    assert rename(client, product_id, headers("bob", "products:*:write")) == 200
    assert rename(client, "research", headers("bob", "products:*:write")) == 200


@pytest.mark.parametrize("isolation", [False, True])
def test_managed_roles_resolve_the_same_grants(tmp_path, isolation):
    from agno.os.authz import Authorization

    db = SqliteDb(db_file=str(tmp_path / "managed.db"))
    authz = Authorization(db=db, verification_keys=[SECRET], audience="scopes", algorithm="HS256")
    authz.define_role("legacy", ["products:read", "products:write"])
    authz.define_role("research", ["products:read", "products:research:write"])
    authz.define_role("owner", ["products:read", "products:own:write"])
    authz.define_role("root", ["agent_os:admin"])
    for subject, role in (("alice", "legacy"), ("bob", "legacy"), ("rita", "research"), ("olga", "owner")):
        authz.assign(subject, role)
    authz.assign("admin", "root")
    agent_os = AgentOS(
        id="scopes",
        db=db,
        agents=[Agent(id="reader", telemetry=False)],
        company=CompanyConfig(products=[Product(id="research", name="Research")]),
        telemetry=False,
        authorization=authz,
        user_isolation=isolation,
    )
    with TestClient(agent_os.get_app()) as client:
        product_id = alice_product(client)
        olga = client.post("/company/products", headers=headers("olga"), json={"name": "Olga's"})
        assert olga.status_code == 201, olga.text
        # A collection grant keeps today's meaning: open without isolation, owner-only with it.
        assert rename(client, product_id, headers("bob")) == (403 if isolation else 200)
        assert rename(client, "research", headers("bob")) == (403 if isolation else 200)
        assert rename(client, product_id, headers("alice")) == 200
        # Matches main: isolation only exempts a token admin scope, not a managed admin role.
        assert rename(client, "research", headers("admin")) == (403 if isolation else 200)
        assert rename(client, "research", headers("rita")) == 200
        assert rename(client, product_id, headers("rita")) == 403
        assert rename(client, olga.json()["id"], headers("olga")) == 200
        assert rename(client, product_id, headers("olga")) == 403
    db.close()
