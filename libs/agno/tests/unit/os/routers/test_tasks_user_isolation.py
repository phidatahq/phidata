"""JWT-backed Task scope and owner-isolation tests."""

import asyncio
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from agno.os import AgentOS, CompanyConfig
from agno.os.config import AuthorizationConfig

SECRET = "company-tasks-isolation-tests"
OS_ID = "company-tasks-tests"
ALL_SCOPES = ["tasks:read", "tasks:write", "tasks:delete"]


def headers(user, scopes=None):
    token = jwt.encode(
        {
            "sub": user,
            "aud": OS_ID,
            "scopes": ALL_SCOPES if scopes is None else scopes,
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        },
        SECRET,
        algorithm="HS256",
    )
    return {"Authorization": "Bearer " + token}


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def make_client(request, tmp_path):
    dbs = []

    def make(isolation):
        cls = AsyncSqliteDb if request.param else SqliteDb
        db = cls(db_file=str(tmp_path / (str(len(dbs)) + ".db")))
        dbs.append(db)
        return TestClient(
            AgentOS(
                id=OS_ID,
                db=db,
                company=CompanyConfig(),
                telemetry=False,
                authorization=True,
                authorization_config=AuthorizationConfig(
                    verification_keys=[SECRET], algorithm="HS256", user_isolation=isolation
                ),
            ).get_app()
        )

    yield make
    for db in dbs:
        if request.param:
            asyncio.run(db.close())
        else:
            db.close()


def create(client, user):
    parent = client.post("/company/products", json={"name": user}, headers=headers(user, ["products:write"])).json()[
        "id"
    ]
    response = client.post("/company/tasks", json={"title": user, "product_id": parent}, headers=headers(user))
    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == user
    return response.json()["id"]


def test_isolation_off_allows_scoped_readers_and_writers(make_client):
    c = make_client(False)
    a, b = create(c, "alice"), create(c, "bob")
    read = headers("reader", ["tasks:read"])
    assert {p["id"] for p in c.get("/company/tasks", headers=read).json()["data"]} == {a, b}
    assert c.get("/company/tasks/" + a, headers=read).status_code == 200
    path = "/company/tasks/" + a
    assert c.patch(path, json={"brief": "Updated"}, headers=headers("bob")).status_code == 200
    assert c.get(path, headers=read).json()["user_id"] == "alice"
    assert c.delete(path, headers=headers("bob")).status_code == 204
    assert c.post(path + "/restore", headers=headers("bob")).status_code == 200


def test_isolation_on_filters_before_pagination_and_hides_foreign_writes(make_client):
    c = make_client(True)
    a = create(c, "alice")
    own = {create(c, "bob") for _ in range(3)}
    pages = [c.get("/company/tasks", params={"limit": 2, "page": p}, headers=headers("bob")).json() for p in (1, 2)]
    assert [len(p["data"]) for p in pages] == [2, 1]
    assert all(p["meta"]["total_count"] == 3 for p in pages)
    assert {row["id"] for p in pages for row in p["data"]} == own
    path = "/company/tasks/" + a
    before = c.get(path, headers=headers("alice")).json()
    for method, suffix, body in [
        ("get", "", None),
        ("patch", "", {"title": "stolen"}),
        ("delete", "", None),
        ("post", "/restore", None),
        ("post", "/transitions", {"target": "cancelled", "reason": "Stop"}),
    ]:
        response = c.request(method, path + suffix, json=body, headers=headers("bob"))
        assert response.status_code == 404, response.text
    assert c.get(path, headers=headers("alice")).json() == before
    assert c.delete(path, headers=headers("alice")).status_code == 204
    assert c.get(path + "?include_deleted=true", headers=headers("bob")).status_code == 404
    assert c.post(path + "/restore", headers=headers("bob")).status_code == 404
    assert c.get("/company/tasks?include_deleted=true", headers=headers("bob")).json()["meta"]["total_count"] == 3
    assert c.post(path + "/restore", headers=headers("alice")).status_code == 200


def test_admin_bypass_and_creator_attribution(make_client):
    c = make_client(True)
    a = create(c, "alice")
    admin = headers("admin", ["agent_os:admin"])
    path = "/company/tasks/" + a
    assert c.get(path, headers=admin).status_code == 200
    assert c.patch(path, json={"title": "renamed"}, headers=admin).status_code == 200
    assert c.delete(path, headers=admin).status_code == 204
    assert c.post(path + "/restore", headers=admin).status_code == 200
    parent = c.post("/company/products", json={"name": "Admin product"}, headers=admin).json()["id"]
    response = c.post("/company/tasks", json={"title": "Admin work", "product_id": parent}, headers=admin)
    assert response.status_code == 201
    assert response.json()["user_id"] == "admin"


@pytest.mark.parametrize("isolation", [False, True])
def test_scopes_apply_to_every_route(make_client, isolation):
    c = make_client(isolation)
    path = "/company/tasks/" + create(c, "alice")
    for method, url, body, scopes in [
        ("get", "/company/tasks", None, ["tasks:write"]),
        ("get", path, None, ["tasks:write"]),
        ("post", "/company/tasks", {"name": "No"}, ["tasks:read"]),
        ("patch", path, {"name": "No"}, ["tasks:read"]),
        ("delete", path, None, ["tasks:write"]),
        ("post", path + "/restore", None, ["tasks:write"]),
        ("post", path + "/transitions", {"target": "cancelled", "reason": "Stop"}, ["tasks:read"]),
    ]:
        assert c.request(method, url, json=body, headers=headers("alice", scopes)).status_code == 403
    assert c.get("/company/tasks").status_code == 401


@pytest.mark.parametrize("authorization", [False, True])
def test_service_account_scopes_on_company_routes(tmp_path, authorization):
    import time

    from agno.os.service_accounts import generate_token

    db = SqliteDb(db_file=str(tmp_path / "service-accounts.db"))
    token, token_hash, token_prefix = generate_token()
    db.create_service_account(
        {
            "id": "reader-id",
            "name": "reader",
            "user_id": "admin",
            "token_hash": token_hash,
            "token_prefix": token_prefix,
            "scopes": ["tasks:read"],
            "created_at": int(time.time()),
            "expires_at": None,
            "last_used_at": None,
            "revoked_at": None,
            "created_by": "admin",
        }
    )
    app = AgentOS(
        id=OS_ID,
        db=db,
        company=CompanyConfig(),
        telemetry=False,
        authorization=authorization,
        authorization_config=AuthorizationConfig(verification_keys=[SECRET], algorithm="HS256")
        if authorization
        else None,
    ).get_app()
    client = TestClient(app)
    auth = {"Authorization": "Bearer " + token}
    assert client.get("/company/tasks", headers=auth).status_code == 200
    assert client.post("/company/tasks", json={"name": "Forbidden"}, headers=auth).status_code == 403
    assert client.patch("/company/tasks/missing", json={"name": "Forbidden"}, headers=auth).status_code == 403
    assert client.delete("/company/tasks/missing", headers=auth).status_code == 403
    assert client.post("/company/tasks/missing/restore", headers=auth).status_code == 403
    db.close()


@pytest.mark.parametrize("enabled", [False, True])
def test_task_scopes_catalog_is_opt_in(enabled):
    from unittest.mock import MagicMock

    from fastapi import FastAPI

    from agno.os.authz.admin_router import get_roles_router

    router = get_roles_router(MagicMock())
    app = FastAPI()
    app.state.company_enabled = enabled
    app.dependency_overrides[router.dependencies[0].dependency] = lambda: "admin"
    app.include_router(router)
    response = TestClient(app).get("/authz/scopes")
    assert response.status_code == 200
    tasks = {item["raw"] for item in response.json() if item["namespace"] == "tasks"}
    assert tasks == (set(ALL_SCOPES) if enabled else set())


@pytest.mark.parametrize("kind,scope", [("agent", "agents"), ("team", "teams"), ("workflow", "workflows")])
def test_ready_requires_accepting_callers_executor_scope(make_client, kind, scope):
    c = make_client(False)
    path = "/company/tasks/" + create(c, "alice")
    body = {"target": "ready", "reason": "Accept", "executor_type": kind, "executor_id": "writer"}
    for scopes in [["tasks:write"], ["tasks:write", scope + ":other:run"], ["tasks:read", scope + ":run"]]:
        assert c.post(path + "/transitions", json=body, headers=headers("bob", scopes)).status_code == 403
    assert c.get(path, headers=headers("alice")).json()["status"] == "backlog"
    accepted = c.post(path + "/transitions", json=body, headers=headers("bob", ["tasks:write", scope + ":writer:run"]))
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted_by"] == "bob"
    assert accepted.json()["executor_id"] == "writer"
    assert isinstance(accepted.json()["accepted_at"], int)


def test_non_run_executor_requires_admin(make_client):
    c = make_client(False)
    path = "/company/tasks/" + create(c, "alice")
    body = {"target": "ready", "reason": "Accept", "executor_type": "engineering", "executor_id": "codex"}
    assert (
        c.post(path + "/transitions", json=body, headers=headers("alice", ["tasks:write", "agents:run"])).status_code
        == 403
    )
    assert c.post(path + "/transitions", json=body, headers=headers("admin", ["agent_os:admin"])).status_code == 200


def test_private_manager_members_cannot_be_accepted(make_client):
    from agno.registry._reserved import RESERVED_MEMBER_IDS

    c = make_client(False)
    path = "/company/tasks/" + create(c, "alice")
    for member in RESERVED_MEMBER_IDS:
        body = {"target": "ready", "reason": "Accept", "executor_type": "agent", "executor_id": member}
        assert c.post(path + "/transitions", json=body, headers=headers("admin", ["agent_os:admin"])).status_code == 409


def test_acceptance_uses_provider_when_token_scopes_are_not_authoritative(monkeypatch):
    from unittest.mock import Mock

    from fastapi import FastAPI, HTTPException
    from starlette.requests import Request

    from agno.os.routers.company.tasks import _require_endpoint_permission

    app = FastAPI()
    request = Request({"type": "http", "app": app})
    request.state.authorization_enabled = True
    request.state.user_id = "alice"
    request.state.scopes = ["agent_os:admin"]
    provider = Mock()
    monkeypatch.setattr("agno.os.auth.caller_scopes_are_authoritative", lambda request: False)
    monkeypatch.setattr("agno.os.auth.resolve_authorization_provider", lambda request: provider)
    provider.check.return_value = False
    with pytest.raises(HTTPException) as exc:
        _require_endpoint_permission(request, "/agents/writer/runs", "POST")
    assert exc.value.status_code == 403
    ctx = provider.check.call_args.args[0]
    assert (ctx.principal_id, ctx.resource_type, ctx.resource_id, ctx.action) == ("alice", "agents", "writer", "run")
    provider.check.return_value = True
    _require_endpoint_permission(request, "/agents/writer/runs", "POST")
    with pytest.raises(HTTPException) as exc:
        _require_endpoint_permission(request, "/engineering/codex/runs", "POST")
    assert exc.value.status_code == 403


def test_custom_admin_scope_is_respected():
    from fastapi import FastAPI, HTTPException
    from starlette.requests import Request

    from agno.os.routers.company.tasks import _require_endpoint_permission

    request = Request({"type": "http", "app": FastAPI()})
    request.state.authorization_enabled = True
    request.state.admin_scope = "custom:admin"
    request.state.scopes = ["agent_os:admin"]
    with pytest.raises(HTTPException):
        _require_endpoint_permission(request, "/engineering/codex/runs", "POST")
    request.state.scopes = ["custom:admin"]
    _require_endpoint_permission(request, "/engineering/codex/runs", "POST")
