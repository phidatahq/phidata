"""Shared write-ownership checks across the Company routers."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, CompanyConfig
from agno.os.config import AuthorizationConfig
from agno.os.routers.company.ownership import _require_write_ownership

SECRET = "company-ownership-tests-signing-secret"
OS_ID = "company-ownership-tests"
SCOPES = [
    "products:read",
    "products:write",
    "products:delete",
    "projects:read",
    "projects:write",
    "projects:delete",
    "tasks:read",
    "tasks:write",
    "tasks:delete",
]


def headers(user, scopes=None):
    token = jwt.encode(
        {
            "sub": user,
            "aud": OS_ID,
            "scopes": SCOPES if scopes is None else scopes,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        },
        SECRET,
        algorithm="HS256",
    )
    return {"Authorization": "Bearer " + token}


@pytest.fixture
def make_client(tmp_path):
    dbs = []

    def make(isolation):
        db = SqliteDb(db_file=str(tmp_path / (str(len(dbs)) + ".db")))
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
        db.close()


def create(client, user, kind):
    product = client.post("/company/products", json={"name": user}, headers=headers(user))
    assert product.status_code == 201, product.text
    if kind == "product":
        return product.json()
    project = client.post(
        "/company/projects", json={"name": user, "product_id": product.json()["id"]}, headers=headers(user)
    )
    assert project.status_code == 201, project.text
    if kind == "project":
        return project.json()
    task = client.post(
        "/company/tasks",
        json={"title": user, "product_id": product.json()["id"], "project_id": project.json()["id"]},
        headers=headers(user),
    )
    assert task.status_code == 201, task.text
    return task.json()


@pytest.mark.parametrize(
    "existing,user_id,detail",
    [
        ({"user_id": "alice"}, "alice", None),
        ({"user_id": "alice"}, None, None),
        ({"user_id": None}, None, None),
        ({"user_id": "alice"}, "bob", "Cannot modify task owned by another user"),
        ({"user_id": None}, "bob", "Cannot modify unowned task"),
    ],
)
def test_helper_checks_scoped_callers_only(existing, user_id, detail):
    if detail is None:
        _require_write_ownership(existing, user_id, "task")
        return
    with pytest.raises(HTTPException) as exc:
        _require_write_ownership(existing, user_id, "task")
    assert exc.value.status_code == 403
    assert exc.value.detail == detail


@pytest.mark.parametrize("kind", ["product", "project", "task"])
def test_isolation_on_owner_writes_and_members_read(make_client, kind):
    client = make_client(True)
    row = create(client, "alice", kind)
    assert row["user_id"] == "alice"
    path = "/company/" + kind + "s/" + row["id"]

    # Any scoped user reads company-wide.
    for user in ("alice", "bob"):
        assert client.get(path, headers=headers(user)).status_code == 200

    # A non-owner cannot delete or restore, and the detail names the record kind.
    denied = client.delete(path, headers=headers("bob"))
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"] == "Cannot modify " + kind + " owned by another user"

    assert client.delete(path, headers=headers("alice")).status_code == 204
    denied = client.post(path + "/restore", headers=headers("bob"))
    assert denied.status_code == 403, denied.text
    assert client.post(path + "/restore", headers=headers("alice")).status_code == 200

    # The creator stays the owner after the round trip.
    assert client.get(path, headers=headers("bob")).json()["user_id"] == "alice"


@pytest.mark.parametrize("kind", ["product", "project", "task"])
def test_isolation_off_keeps_unscoped_writes_and_caller_attribution(make_client, kind):
    client = make_client(False)
    row = create(client, "alice", kind)
    # Without isolation the caller is still recorded as the creator.
    assert row["user_id"] == "alice"
    path = "/company/" + kind + "s/" + row["id"]
    assert client.get(path, headers=headers("bob")).status_code == 200
    assert client.delete(path, headers=headers("bob")).status_code == 204
    assert client.post(path + "/restore", headers=headers("bob")).status_code == 200
    assert client.get(path, headers=headers("bob")).json()["user_id"] == "alice"


def test_isolation_on_owner_edits_product_and_member_cannot(make_client):
    client = make_client(True)
    row = create(client, "alice", "product")
    path = "/company/products/" + row["id"]
    denied = client.patch(path, json={"name": "Renamed"}, headers=headers("bob"))
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"] == "Cannot modify product owned by another user"
    response = client.patch(path, json={"name": "Renamed"}, headers=headers("alice"))
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Renamed"
