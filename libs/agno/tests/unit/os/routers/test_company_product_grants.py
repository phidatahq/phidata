"""Product writes take per-record grants: products:<id|own|*>:<action>, with existing scopes unchanged."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.company import Product
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, CompanyConfig
from agno.os.authz.records import RecordGrant
from agno.os.config import AuthorizationConfig

SECRET = "company-product-grants-secret-at-least-32-bytes"
READ = ["products:read", "routines:read"]
ROUTINE_SCOPES = ["routines:write", "schedules:write", "agents:reader:run"]


def headers(user, *scopes, read=True):
    claims = {
        "sub": user,
        "aud": "grants",
        "scopes": [*(READ if read else []), *scopes],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return {"Authorization": "Bearer " + jwt.encode(claims, SECRET, algorithm="HS256")}


def build(tmp_path, authorization=True, **kwargs):
    db = SqliteDb(db_file=str(tmp_path / "grants.db"))
    agent_os = AgentOS(
        id="grants",
        db=db,
        agents=[Agent(id="reader", telemetry=False)],
        company=CompanyConfig(products=[Product(id="research", name="Research")]),
        telemetry=False,
        authorization=authorization,
        **kwargs,
    )
    return agent_os, db


@pytest.fixture
def client(tmp_path, request):
    agent_os, db = build(
        tmp_path,
        authorization_config=AuthorizationConfig(
            verification_keys=[SECRET], algorithm="HS256", user_isolation=request.param
        ),
    )
    with TestClient(agent_os.get_app()) as test_client:
        yield test_client
    db.close()


def edit(client, product_id, caller):
    response = client.patch("/company/products/" + product_id, headers=caller, json={"purpose": "edited"})
    if response.status_code == 200:
        assert response.json()["purpose"] == "edited" and response.json()["updated_at"] is not None
    return response.status_code


def alice_product(client):
    response = client.post("/company/products", headers=headers("alice", "products:write"), json={"name": "Alice's"})
    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == "alice"
    return response.json()["id"]


def test_record_grant_reads_provider_ids_and_isolation_narrows_every_record():
    assert RecordGrant.from_ids({"*"}) == RecordGrant(every=True)
    assert RecordGrant.from_ids({"own", "research"}) == RecordGrant(own=True, ids=frozenset({"research"}))
    assert RecordGrant.from_ids(set()).empty
    assert RecordGrant(every=True).isolated() == RecordGrant(own=True)
    assert RecordGrant(ids=frozenset({"research"})).isolated() == RecordGrant(ids=frozenset({"research"}))


@pytest.mark.parametrize("client", [True], indirect=True)
def test_existing_scopes_under_isolation_stay_owner_only(client):
    product_id = alice_product(client)
    assert edit(client, product_id, headers("alice", "products:write")) == 200
    assert edit(client, product_id, headers("bob", "products:write")) == 403
    assert edit(client, "research", headers("bob", "products:write")) == 403
    assert edit(client, "research", headers("bob", "products:*:write")) == 403
    # The denial explains the ownership rule, as before, not a scope the caller already holds.
    other = client.patch("/company/products/" + product_id, headers=headers("bob", "products:write"), json={})
    assert other.json()["detail"] == "Cannot modify product owned by another user"
    unowned = client.patch("/company/products/research", headers=headers("bob", "products:write"), json={})
    assert unowned.json()["detail"] == "Cannot modify unowned product"
    assert edit(client, "research", headers("root", "agent_os:admin")) == 200


@pytest.mark.parametrize("client", [False], indirect=True)
def test_existing_scopes_without_isolation_stay_open(client):
    product_id = alice_product(client)
    assert edit(client, product_id, headers("bob", "products:write")) == 200
    assert edit(client, "research", headers("bob", "products:write")) == 200


@pytest.mark.parametrize("client", [False, True], indirect=True)
def test_a_named_product_grant_covers_that_product_only(client):
    product_id = alice_product(client)
    bob = headers("bob", "products:research:write")
    assert edit(client, "research", bob) == 200
    assert edit(client, product_id, bob) == 403
    created = client.post(
        "/company/routines",
        headers=headers("bob", "products:research:write", *ROUTINE_SCOPES),
        json=dict(product_id="research", name="intake", template="intake", executor_type="agent", executor_id="reader"),
    )
    assert created.status_code == 201, created.text
    assert created.json()["user_id"] == "bob"
    # A named grant does not create Products, and write does not imply delete.
    assert client.post("/company/products", headers=bob, json={"name": "New"}).status_code == 403
    assert client.delete("/company/products/research", headers=bob).status_code == 403
    deleter = headers("bob", "products:research:delete")
    assert client.delete("/company/products/research", headers=deleter).status_code == 204
    assert client.post("/company/products/research/restore", headers=deleter).status_code == 200


@pytest.mark.parametrize("client", [False, True], indirect=True)
def test_an_own_grant_covers_the_callers_products(client):
    product_id = alice_product(client)
    assert edit(client, product_id, headers("alice", "products:own:write")) == 200
    assert edit(client, product_id, headers("bob", "products:own:write")) == 403
    assert edit(client, "research", headers("bob", "products:own:write")) == 403
    created = client.post("/company/products", headers=headers("bob", "products:own:write"), json={"name": "Bob's"})
    assert created.status_code == 201 and created.json()["user_id"] == "bob"
    assert edit(client, created.json()["id"], headers("bob", "products:own:write")) == 200
    # A missing Product is still a 404, not a denial.
    assert edit(client, "missing", headers("bob", "products:own:write")) == 404


@pytest.mark.parametrize("client", [True], indirect=True)
def test_routes_under_a_product_that_need_another_scope_are_not_product_writes(client):
    # Wiki pages live under the Product's path but require wiki:write, not a Product grant.
    page = client.put(
        "/company/products/research/wiki/notes.md",
        headers=headers("bob", "wiki:read", "wiki:write"),
        json={"content": "Notes"},
    )
    assert page.status_code not in (401, 403), page.text


@pytest.mark.parametrize("isolation", [False, True])
def test_managed_roles_resolve_the_same_grants(tmp_path, isolation):
    from agno.os.authz import Authorization

    db = SqliteDb(db_file=str(tmp_path / "managed.db"))
    authz = Authorization(db=db, verification_keys=[SECRET], audience="grants", algorithm="HS256")
    authz.define_role("member", ["products:read", "products:write"])
    authz.define_role("research", ["products:read", "products:research:write"])
    authz.define_role("owner", ["products:read", "products:own:write"])
    authz.define_role("admin", ["agent_os:admin"])
    authz.assign("root", "admin")
    for subject, role in (("alice", "member"), ("bob", "member"), ("rita", "research"), ("olga", "owner")):
        authz.assign(subject, role)
    agent_os = AgentOS(
        id="grants",
        db=db,
        agents=[Agent(id="reader", telemetry=False)],
        company=CompanyConfig(products=[Product(id="research", name="Research")]),
        telemetry=False,
        authorization=authz,
        user_isolation=isolation,
    )
    with TestClient(agent_os.get_app()) as client:
        product_id = client.post("/company/products", headers=headers("alice", read=False), json={"name": "A"}).json()[
            "id"
        ]
        olga = client.post("/company/products", headers=headers("olga", read=False), json={"name": "Olga's"})
        assert olga.status_code == 201, olga.text
        assert edit(client, product_id, headers("bob", read=False)) == (403 if isolation else 200)
        assert edit(client, "research", headers("bob", read=False)) == (403 if isolation else 200)
        assert edit(client, product_id, headers("alice", read=False)) == 200
        assert edit(client, "research", headers("rita", read=False)) == 200
        assert edit(client, product_id, headers("rita", read=False)) == 403
        assert edit(client, olga.json()["id"], headers("olga", read=False)) == 200
        assert edit(client, product_id, headers("olga", read=False)) == 403
        catalog = {
            item["raw"] for item in client.get("/authz/scopes", headers=headers("root", "agent_os:admin")).json()
        }
    assert {"products:own:write", "products:research:write", "products:research:delete"} <= catalog
    db.close()


def test_without_the_route_gate_isolation_keeps_the_owner_check(tmp_path):
    from agno.os.middleware.jwt import JWTMiddleware

    agent_os, db = build(tmp_path, authorization=False)
    app = agent_os.get_app()
    # Authentication and isolation without the scope gate: a hand-wired JWTMiddleware.
    app.add_middleware(
        JWTMiddleware, verification_keys=[SECRET], algorithm="HS256", authorization=False, user_isolation=True
    )
    with TestClient(app) as client:
        product_id = alice_product(client)
        assert edit(client, product_id, headers("alice")) == 200
        assert edit(client, product_id, headers("bob", "products:research:write")) == 403
        assert edit(client, "research", headers("bob", "products:research:write")) == 403
    db.close()
