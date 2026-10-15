"""Model-free tests against a disposable PostgreSQL database.

Set COMPANY_TEST_DATABASE_URL to a dedicated database; this suite resets only
its agno_company schema. Never point this at a deployment database.
"""

import asyncio
import inspect
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, Authorization, CompanyConfig
from agno.os.authz.scope_provider import ScopeAuthorizationProvider
from agno.os.company.migrations import migrate
from agno.os.company.policy import CompanyError, Principal
from agno.os.company.schemas import (
    CommentCreate,
    ListQuery,
    MemberCreate,
    MemberPatch,
    ProductCreate,
    ProductPatch,
    ProjectCreate,
    Reason,
    TaskCreate,
    TaskPatch,
    Transition,
)
from agno.os.company.service import CompanyService

KEY = "company-local-test-key-with-at-least-32-bytes"
SCOPES = (
    "config:read",
    "company:manage",
    "company_products:read",
    "company_products:write",
    "company_products:review",
    "company_products:manage",
)


def principal(who="alice", scopes=SCOPES):
    return Principal(who, ScopeAuthorizationProvider(), tuple(scopes))


def mutation(**kwargs):
    return {"principal": principal(), "request_id": str(uuid4()), "idempotency_key": str(uuid4()), **kwargs}


def journey(service):
    product = service.create_product(
        data=ProductCreate(name="Website", instructions="Helpful website", owner_id="alice"), **mutation()
    )
    project = service.create_project(
        product_id=product["id"],
        data=ProjectCreate(
            title="Improve onboarding",
            instructions="Guide works",
            owner_id="alice",
        ),
        **mutation(),
    )
    task = service.create_task(
        product_id=product["id"],
        data=TaskCreate(
            project_id=project["id"],
            title="Correct the setup guide",
            instructions="Install on a clean machine",
            accountable_owner_id="alice",
        ),
        **mutation(),
    )
    return product, project, task


def transition(service, task, to_status, **data):
    return service.transition_task(
        task_id=task["id"], version=task["version"], data=Transition(to_status=to_status, **data), **mutation()
    )


def test_persistence_journey_and_explicit_review(setup):
    db, users, service = setup
    product, project, task = journey(service)
    for status in ("ready", "in_progress", "in_review"):
        task = transition(service, task, status)
    with pytest.raises(CompanyError, match="reason"):
        transition(service, task, "done")
    with pytest.raises(CompanyError, match="evidence"):
        transition(service, task, "done", reason="Looks good")
    task = transition(
        service,
        task,
        "done",
        reason="Fresh installation works",
        acceptance_check="Executed the documented steps in a clean environment",
    )
    fresh = CompanyService(CompanyConfig(db=db), users)
    assert fresh.get_task(principal=principal(), task_id=task["id"])["status"] == "done"
    counts = fresh.get_project(principal=principal(), project_id=project["id"])["counts"]
    assert counts["accepted_tasks"] == counts["done_tasks"] == 1
    assert counts["in_review"] == 0
    assert len(fresh.list_activity(principal=principal())["data"]) == 7
    assert fresh.list_products(principal=principal("mallory"))["data"] == []
    with pytest.raises(CompanyError) as denied:
        fresh.get_task(principal=principal("mallory"), task_id=task["id"])
    assert denied.value.status == 404


def test_roles_scope_filters_and_revocation_before_replay(setup):
    db, users, service = setup
    product, project, task = journey(service)
    for who, role in (("bob", "contributor"), ("reader", "reader")):
        added = service.add_member(
            product_id=product["id"],
            version=product["version"],
            data=MemberCreate(principal_id=who, role=role),
            **mutation(),
        )
        product["version"] = added["version"]
    private = service.create_product(
        data=ProductCreate(name="Legal", instructions="Private", owner_id="alice"), **mutation()
    )
    assert len(service.list_products(principal=principal("reader"))["data"]) == 1
    assert service.list_products(principal=principal("reader"))["data"][0]["counts"]["accepted_tasks"] == 0
    with pytest.raises(CompanyError) as denied:
        service.update_task(
            task_id=task["id"],
            version=1,
            data=TaskPatch(title="Not allowed"),
            **mutation(principal=principal("reader")),
        )
    assert denied.value.status == 403
    scoped = principal("alice", (f"company_products:{product['id']}:read",))
    page = service.list_products(principal=scoped, query=ListQuery(limit=1))
    assert [r["id"] for r in page["data"]] == [UUID_or_string(product["id"])]
    assert page["next_cursor"] is None
    request = mutation(principal=principal("bob"))
    replayed = service.create_task(product_id=product["id"], data=TaskCreate(title="Backlog"), **request)
    service.update_member(
        product_id=product["id"],
        member_id="bob",
        version=product["version"],
        data=MemberPatch(role="contributor", active=False),
        **mutation(),
    )
    with pytest.raises(CompanyError) as denied:
        service.create_task(product_id=product["id"], data=TaskCreate(title="Backlog"), **request)
    assert denied.value.status == 404
    users.set_disabled("reader", True)
    with pytest.raises(CompanyError):
        service.list_tasks(principal=principal("reader"))
    assert private["id"] != replayed["product_id"]


def UUID_or_string(value):
    from uuid import UUID

    return UUID(value)


def test_parent_constraint_and_archive(setup):
    db, users, service = setup
    product, project, task = journey(service)
    other = service.create_product(
        data=ProductCreate(name="Other", instructions="Other", owner_id="alice"), **mutation()
    )
    with pytest.raises(CompanyError) as conflict:
        service.create_task(
            product_id=other["id"], data=TaskCreate(title="Wrong", project_id=project["id"]), **mutation()
        )
    assert conflict.value.status == 409
    with pytest.raises(IntegrityError), db.db_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO agno_company.tasks(id,key,product_id,project_id,title) VALUES(:id,:key,:pid,:project,'Wrong')"
            ),
            dict(id=str(uuid4()), key=str(uuid4()), pid=other["id"], project=project["id"]),
        )
    archived = service.archive_product(product_id=product["id"], version=1, data=Reason(reason="Paused"), **mutation())
    with pytest.raises(CompanyError, match="Restore"):
        service.create_task(product_id=product["id"], data=TaskCreate(title="Blocked"), **mutation())
    restored = service.restore_product(
        product_id=product["id"], version=archived["version"], data=Reason(reason="Resume"), **mutation()
    )
    assert restored["id"] == product["id"]
    assert service.get_task(principal=principal(), task_id=task["id"])["version"] == 1


def test_idempotency_concurrent_edits_and_atomic_activity(setup):
    db, users, service = setup
    request = mutation()
    data = ProductCreate(name="Website", instructions="Purpose", owner_id="alice")
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: service.create_product(data=data, **request), range(2)))
    assert results[0] == results[1]
    product = results[0]
    with pytest.raises(CompanyError) as conflict:
        service.create_product(data=data.model_copy(update={"name": "Different"}), **request)
    assert conflict.value.status == 409

    def edit(name):
        try:
            service.update_product(product_id=product["id"], version=1, data=ProductPatch(name=name), **mutation())
            return 200
        except CompanyError as exc:
            return exc.status

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(edit, ("One", "Two"))) == [200, 412]
    assert len(service.list_activity(principal=principal())["data"]) == 2


def test_archive_create_race(setup):
    db, users, service = setup
    product, project, task = journey(service)

    def write(which):
        try:
            if which == "archive":
                return service.archive_product(
                    product_id=product["id"], version=1, data=Reason(reason="Pause"), **mutation()
                )
            return service.create_task(product_id=product["id"], data=TaskCreate(title="Race"), **mutation())
        except CompanyError as exc:
            return exc.status

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(write, ("archive", "create")))
    assert results[0]["state"] == "archived"
    assert isinstance(results[1], dict) or results[1] == 409
    events = service.list_activity(principal=principal())["data"]
    assert events[-1]["operation"] == "product.archive"


def test_acceptance_membership_and_review_locks(setup):
    db, users, service = setup
    product, project, task = journey(service)
    with pytest.raises(CompanyError):
        service.update_member(
            product_id=product["id"], member_id="alice", version=1, data=MemberPatch(role="reader"), **mutation()
        )
    with pytest.raises(CompanyError):
        transition(service, task, "done", reason="Skipped")
    blank = service.create_task(product_id=product["id"], data=TaskCreate(title="Unplanned"), **mutation())
    with pytest.raises(CompanyError):
        transition(service, blank, "ready")
    for status in ("ready", "in_progress", "in_review"):
        task = transition(service, task, status)
    with pytest.raises(CompanyError, match="Return or reopen"):
        service.update_task(task_id=task["id"], version=task["version"], data=TaskPatch(evidence=[]), **mutation())
    task = transition(service, task, "in_progress", reason="Please fix the examples")
    assert task["status"] == "in_progress"
    comment = service.add_comment_task(task_id=task["id"], data=CommentCreate(body="Working on it"), **mutation())
    assert comment["author_id"] == "alice"
    assert (
        service.list_comments(principal=principal(), kind="task", record_id=task["id"])["data"][0]["body"]
        == "Working on it"
    )


@pytest.mark.asyncio
async def test_async_transaction_off_event_loop(setup, monkeypatch):
    db, users, service = setup
    journey(service)
    original = service.list_products

    def slow(**kwargs):
        time.sleep(0.15)
        return original(**kwargs)

    monkeypatch.setattr(service, "list_products", slow)
    task = asyncio.create_task(service.alist_products(principal=principal()))
    await asyncio.sleep(0.03)
    assert not task.done()
    assert (await task)["data"]
    for name, method in inspect.getmembers(CompanyService, inspect.isfunction):
        if not name.startswith(("_", "a")):
            assert hasattr(CompanyService, "a" + name)


def token(who="alice", scopes=SCOPES):
    return jwt.encode(
        {"sub": who, "scopes": list(scopes), "exp": int(time.time()) + 3600, "aud": "company-test"},
        KEY,
        algorithm="HS256",
    )


def test_http_conditional_routes_auth_etags_schema_and_resync(setup):
    db, users, service = setup
    auth = Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test")
    os_app = AgentOS(id="company-test", company=CompanyConfig(db=db), authorization=auth)
    app = os_app.get_app()
    with TestClient(app) as client:
        assert client.get("/company/v1/products").status_code == 401
        client.headers["Authorization"] = "Bearer " + token()
        assert client.get("/config").json()["company"]["renderer_version"] == "company.v1"
        body = {"name": "Website", "instructions": "Helpful", "owner_id": "alice"}
        response = client.post("/company/v1/products", json=body, headers={"Idempotency-Key": "http-create"})
        assert response.status_code == 201, response.text
        product = response.json()
        assert response.headers["ETag"] == '"1"'
        assert response.headers["X-Request-ID"]
        url = "/company/v1/products/" + product["id"]
        bad = client.patch(url, json={"owner_id": "mallory"}, headers={"Idempotency-Key": "forged", "If-Match": '"1"'})
        assert bad.status_code == 422 and "error" in bad.json()
        missing = client.patch(url, json={"name": "Changed"}, headers={"Idempotency-Key": "missing"})
        assert missing.status_code == 428
        assert client.get("/company/v1/products?limit=101").status_code == 422
        before = list(app.openapi()["paths"])
        os_app.resync(app)
        assert list(app.openapi()["paths"]) == before
        company_routes = [
            (r.path, tuple(sorted(r.methods))) for r in app.routes if getattr(r, "path", "").startswith("/company")
        ]
        assert len(company_routes) == len(set(company_routes))
        client.headers["Authorization"] = "Bearer " + token("mallory", ("agent_os:admin", "config:read"))
        assert "company" not in client.get("/config").json()
        assert client.get(url).status_code == 404
        client.headers["Authorization"] = "Bearer " + token("reader", ("company_products:read", "config:read"))
        assert client.post("/agents/test/runs", data={"message": "forbidden"}).status_code in (403, 404)


@pytest.mark.parametrize("kwargs", [{}, {"company": None}])
def test_disabled_no_import_or_side_effect(kwargs):
    app_os = AgentOS(db=SqliteDb(db_url="sqlite:///:memory:"), **kwargs)
    app = app_os.get_app()
    assert app_os.company is None
    assert not any(p.startswith("/company") for p in app.openapi()["paths"])
    with TestClient(app) as client:
        assert "company" not in client.get("/config").json()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from agno.os import CompanyConfig, AgentOS; assert 'agno.os.company.service' not in sys.modules; assert 'agno.os.company.migrations' not in sys.modules",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_configuration_errors(setup):
    db, _, _ = setup
    with pytest.raises(ValueError, match="PostgresDb"):
        CompanyConfig(db=SqliteDb(db_url="sqlite:///:memory:"))
    with pytest.raises(ValueError, match="authorization"):
        AgentOS(company=CompanyConfig(db=db))
    with pytest.raises(ValueError):
        AgentOS(company=True, authorization=True)


def test_contributor_transition_replay_and_project_completion(setup):
    _, _, service = setup
    product, project, task = journey(service)
    service.add_member(
        product_id=product["id"], version=1, data=MemberCreate(principal_id="bob", role="contributor"), **mutation()
    )
    task = transition(service, task, "ready")
    for status in ("in_progress", "in_review"):
        request = mutation(principal=principal("bob"))
        data = Transition(to_status=status)
        first = service.transition_task(task_id=task["id"], version=task["version"], data=data, **request)
        assert service.transition_task(task_id=task["id"], version=task["version"], data=data, **request) == first
        task = first
    assert service.get_project(principal=principal(), project_id=project["id"])["status"] == "active"
    task = transition(service, task, "done", reason="Fresh install verified", acceptance_check="Checks passed")
    assert service.get_project(principal=principal(), project_id=project["id"])["status"] == "completed"
    service.create_task(
        product_id=product["id"], data=TaskCreate(title="Follow up", project_id=project["id"]), **mutation()
    )
    assert service.get_project(principal=principal(), project_id=project["id"])["status"] == "active"
    reopened = transition(service, task, "backlog", reason="More work")
    assert reopened["accepted_at"] is None


def test_pagination_filters_scoped_cursors_and_disabled_scope(setup):
    _, _, service = setup
    product, project, task = journey(service)
    for i in range(3):
        service.create_task(product_id=product["id"], data=TaskCreate(title=f"Routine {i}"), **mutation())
    assert len(service.list_tasks(principal=principal(), query=ListQuery(key=task["key"]))["data"]) == 1
    page = service.list_tasks(principal=principal(), query=ListQuery(limit=2))
    assert len(page["data"]) == 2 and page["next_cursor"]
    second = service.list_tasks(principal=principal(), query=ListQuery(limit=2, cursor=page["next_cursor"]))
    assert len(second["data"]) == 2 and second["next_cursor"] is None
    assert {str(t["id"]) for t in page["data"]}.isdisjoint(str(t["id"]) for t in second["data"])
    with pytest.raises(CompanyError):
        service.list_tasks(principal=principal(), query=ListQuery(cursor=page["next_cursor"], status="in_review"))
    assert len(service.list_tasks(principal=principal(), query=ListQuery(direct=True))["data"]) == 3
    with pytest.raises(CompanyError) as mismatch:
        service.get_task(principal=principal(), task_id=task["id"], project_id=str(uuid4()))
    assert mismatch.value.status == 404
    assert service.list_products(principal=principal(scopes=("agents:read",)))["data"] == []


def test_schema_check_and_migration_idempotency(setup):
    db, _, service = setup
    product, _, _ = journey(service)
    migrate(db)
    assert service.get_product(principal=principal(), product_id=product["id"])["version"] == 1
    with db.db_engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO agno_company.schema_version(version) VALUES(99)")
    with pytest.raises(CompanyError) as error:
        service.list_products(principal=principal())
    assert error.value.code == "schema_required"
    with pytest.raises(RuntimeError):
        migrate(db)


def test_http_error_envelope_and_contextual_task(setup):
    db, _, _ = setup
    os_app = AgentOS(
        id="company-test",
        company=CompanyConfig(db=db),
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
    )
    with TestClient(os_app.get_app()) as client:
        unauthorized = client.get("/company/v1/products")
        assert unauthorized.status_code == 401 and "error" in unauthorized.json()
        assert unauthorized.json()["request_id"] == unauthorized.headers["X-Request-ID"]
        client.headers["Authorization"] = "Bearer " + token()
        response = client.post(
            "/company/v1/products",
            json={"name": "Website", "instructions": "Purpose", "owner_id": "alice"},
            headers={"Idempotency-Key": "create"},
        )
        product = response.json()
        assert response.status_code == 201
        project = client.post(
            f"/company/v1/products/{product['id']}/projects",
            json={"title": "Onboard", "instructions": "Works", "owner_id": "alice"},
            headers={"Idempotency-Key": "project"},
        ).json()
        task = client.post(
            f"/company/v1/products/{product['id']}/tasks",
            json={"title": "Guide", "project_id": project["id"]},
            headers={"Idempotency-Key": "task"},
        ).json()
        assert client.get(f"/company/v1/tasks/{task['id']}?project_id={uuid4()}").status_code == 404
        assert client.get(f"/company/v1/tasks/{task['id']}?project_id={project['id']}").status_code == 200
        assert client.get(f"/company/v1/tasks?direct=true&project_id={project['id']}").status_code == 422
        forged = client.post(
            f"/company/v1/products/{product['id']}/tasks",
            json={"title": "Forge", "origin": "agent", "actor_id": "alice"},
            headers={"Idempotency-Key": "forged"},
        )
        assert forged.status_code == 422


def test_return_archive_and_reopen_graphs(setup):
    _, _, service = setup
    product, project, task = journey(service)
    for target in (
        "ready",
        "backlog",
        "ready",
        "in_progress",
        "in_review",
        "in_progress",
        "in_review",
        "done",
        "backlog",
    ):
        task = transition(service, task, target, reason="Human decision", acceptance_check="Verified")
        assert task["status"] == target
        with pytest.raises(CompanyError):
            transition(service, task, target, reason="Same state")
    for kind, record in (("task", task), ("project", project)):
        for action, state in (("archive", "archived"), ("restore", "active")):
            record = getattr(service, action + "_" + kind)(
                **{kind + "_id": record["id"]},
                version=record["version"],
                data=Reason(reason="Human decision"),
                **mutation(),
            )
            assert record["state"] == state


def test_creation_does_not_connect_or_run_ddl(setup, monkeypatch):
    db, _, _ = setup

    def forbidden(*args, **kwargs):
        raise AssertionError("Company startup must not connect or migrate")

    monkeypatch.setattr(db.db_engine, "connect", forbidden)
    config = CompanyConfig(db=db)
    os_app = AgentOS(
        id="company-test",
        company=config,
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
    )
    app = os_app.get_app()
    assert "/company/v1/products" in app.openapi()["paths"]
    os_app.resync(app)
    assert "/company/v1/products" in app.openapi()["paths"]


def test_disabled_identity_and_revoked_action_cannot_replay(setup):
    _, users, service = setup
    product, _, task = journey(service)
    request = mutation()
    data = TaskPatch(title="Updated title")
    service.update_task(task_id=task["id"], version=1, data=data, **request)
    with pytest.raises(CompanyError) as denied:
        service.update_task(
            task_id=task["id"],
            version=1,
            data=data,
            **{**request, "principal": principal(scopes=("company_products:read",))},
        )
    assert denied.value.status == 403
    users.set_disabled("alice", True)
    with pytest.raises(CompanyError):
        service.update_task(task_id=task["id"], version=1, data=data, **request)


def test_minimal_http_records_and_growing_task_into_project(setup):
    db, users, service = setup
    app = AgentOS(
        id="company-test",
        company=CompanyConfig(db=db),
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
    ).get_app()
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + token()

        def create(path, body, key):
            response = client.post("/company/v1" + path, json=body, headers={"Idempotency-Key": key})
            assert response.status_code == 201, response.text
            return response.json()

        product = create("/products", {"name": "Frontend"}, "simple-product")
        assert product["owner_id"] == "alice" and product["instructions"] == ""
        assert create("/products", {"name": "Frontend"}, "simple-product")["id"] == product["id"]
        task = create("/products/" + product["id"] + "/tasks", {"title": "Improve navigation"}, "simple-task")
        assert task["project_id"] is None and task["accountable_owner_id"] == "alice"
        assert task["status"] == "backlog" and task["accepted_at"] is None
        project = create("/products/" + product["id"] + "/projects", {"title": "Navigation redesign"}, "simple-project")
        assert project["owner_id"] == "alice" and project["status"] == "empty"
        assert project["instructions"] == ""
        path = "/company/v1/tasks/" + task["id"]
        headers = {"Idempotency-Key": "attach-project", "If-Match": '"1"'}
        response = client.patch(path, json={"project_id": project["id"]}, headers=headers)
        assert response.status_code == 200, response.text
        attached = response.json()
        assert attached["id"] == task["id"] and attached["project_id"] == project["id"]
        assert attached["version"] == 2 and attached["accountable_owner_id"] == "alice"
        assert client.patch(path, json={"project_id": project["id"]}, headers=headers).json() == attached
        conflict = client.patch(path, json={"project_id": None}, headers={**headers, "Idempotency-Key": "stale"})
        assert conflict.status_code == 412
        response = client.patch(
            path, json={"project_id": None}, headers={"Idempotency-Key": "detach-project", "If-Match": '"2"'}
        )
        assert response.status_code == 200, response.text
        assert response.json()["id"] == task["id"] and response.json()["project_id"] is None
        assert len(client.get("/company/v1/tasks?direct=true").json()["data"]) == 1
        assert client.get("/company/v1/tasks?project_id=" + project["id"]).json()["data"] == []
        events = client.get("/company/v1/activity?subject_type=task&subject_id=" + task["id"]).json()["data"]
        assert [event["operation"] for event in events] == ["task.create", "task.edit", "task.edit"]
        assert all(event["actor_id"] == "alice" for event in events)


def test_default_ownership_and_project_association_boundaries(setup):
    db, users, service = setup
    product = service.create_product(data=ProductCreate(name="Backend"), **mutation())
    service.add_member(
        product_id=product["id"], version=1, data=MemberCreate(principal_id="bob", role="contributor"), **mutation()
    )
    project = service.create_project(
        product_id=product["id"], data=ProjectCreate(title="API overhaul", owner_id="bob"), **mutation()
    )
    task = service.create_task(
        product_id=product["id"], data=TaskCreate(title="Audit endpoints", project_id=project["id"]), **mutation()
    )
    assert task["accountable_owner_id"] == "bob"
    direct = service.create_task(
        product_id=product["id"], data=TaskCreate(title="Investigate latency"), **mutation(principal=principal("bob"))
    )
    assert direct["accountable_owner_id"] == "alice"
    other = service.create_product(data=ProductCreate(name="Legal"), **mutation())
    outside = service.create_project(product_id=other["id"], data=ProjectCreate(title="Contracts"), **mutation())
    with pytest.raises(CompanyError, match="same Product"):
        service.update_task(task_id=direct["id"], version=1, data=TaskPatch(project_id=outside["id"]), **mutation())
    service.archive_project(project_id=project["id"], version=1, data=Reason(reason="Deferred"), **mutation())
    with pytest.raises(CompanyError, match="open Project"):
        service.update_task(task_id=direct["id"], version=1, data=TaskPatch(project_id=project["id"]), **mutation())
    with pytest.raises(CompanyError) as denied:
        service.update_task(
            task_id=direct["id"], version=1, data=TaskPatch(project_id=None), **mutation(principal=principal("mallory"))
        )
    assert denied.value.status == 404
    assert service.get_task(principal=principal(), task_id=direct["id"])["version"] == 1


def test_accepted_task_association_preserves_review_and_counts(setup):
    db, users, service = setup
    product, project, task = journey(service)
    service.add_member(
        product_id=product["id"], version=1, data=MemberCreate(principal_id="bob", role="contributor"), **mutation()
    )
    task = transition(service, task, "ready")
    with pytest.raises(CompanyError) as denied:
        service.update_task(
            task_id=task["id"],
            version=task["version"],
            data=TaskPatch(project_id=None),
            **mutation(principal=principal("bob")),
        )
    assert denied.value.status == 403
    service.update_member(
        product_id=product["id"], member_id="bob", version=2, data=MemberPatch(role="owner"), **mutation()
    )
    request = dict(
        task_id=task["id"],
        version=task["version"],
        data=TaskPatch(project_id=None),
        **mutation(principal=principal("bob")),
    )
    task = service.update_task(**request)
    service.update_member(
        product_id=product["id"], member_id="bob", version=3, data=MemberPatch(role="contributor"), **mutation()
    )
    with pytest.raises(CompanyError) as replay_denied:
        service.update_task(**request)
    assert replay_denied.value.status == 403
    assert task["accepted_at"] is None
    assert task["status"] == "backlog"
    assert service.get_project(principal=principal(), project_id=project["id"])["counts"]["accepted_tasks"] == 0
    assert service.get_product(principal=principal(), product_id=product["id"])["counts"]["accepted_tasks"] == 0
    task = service.update_task(
        task_id=task["id"], version=task["version"], data=TaskPatch(project_id=project["id"]), **mutation()
    )
    task = transition(service, task, "ready")
    for status in ("in_progress", "in_review"):
        task = transition(service, task, status)
    with pytest.raises(CompanyError, match="Return or reopen"):
        service.update_task(
            task_id=task["id"], version=task["version"], data=TaskPatch(project_id=project["id"]), **mutation()
        )


def test_company_inherits_database_and_explicit_override_wins(setup):
    db, _, _ = setup
    auth = Authorization(verification_keys=[KEY], algorithm="HS256")
    inherited = AgentOS(db=db, company=CompanyConfig(), authorization=auth)
    assert inherited.company._engine is db.db_engine
    other = PostgresDb(db_url="postgresql+psycopg://unused:unused@localhost/unused")
    explicit = AgentOS(db=other, company=CompanyConfig(db=db), authorization=auth)
    assert explicit.company._engine is db.db_engine
    with pytest.raises(ValueError, match="PostgreSQL database"):
        AgentOS(company=CompanyConfig(), authorization=auth)
    with pytest.raises(ValueError, match="PostgresDb"):
        AgentOS(db=SqliteDb(db_url="sqlite:///:memory:"), company=CompanyConfig(), authorization=auth)
