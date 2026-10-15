"""Durable Company files share record permissions and atomic transactions."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_manual import KEY, mutation, principal, token, transition

from agno.os import AgentOS, Authorization, CompanyConfig
from agno.os.company.policy import CompanyError
from agno.os.company.schemas import MemberCreate, ProductCreate
from agno.os.company.service import CompanyService


def create(service, name="Docs"):
    return service.create_product(data=ProductCreate(name=name), **mutation())


def write(service, product_id=None, **kwargs):
    return service.files.write(
        product_id=product_id,
        path="brief.md",
        content="  Useful facts\n",
        expected_version=kwargs.pop("expected_version", 0),
        **{**mutation(), **kwargs},
    )


def test_files_persist_share_and_enforce_scope(setup):
    db, users, service = setup
    product = create(service)
    pid = product["id"]
    result = write(service, pid)
    assert result["version"] == 1
    service.add_member(
        product_id=pid,
        version=product["version"],
        data=MemberCreate(principal_id="reader", role="reader"),
        **mutation(),
    )
    fresh = CompanyService(CompanyConfig(db=db), users)
    assert (
        fresh.files.read(principal=principal("reader"), product_id=pid, path="brief.md")["content"]
        == "  Useful facts\n"
    )
    assert len(fresh.files.list(principal=principal("reader"), product_id=pid, query="USEFUL")["data"]) == 1
    for operation in [
        lambda: fresh.files.read(principal=principal("mallory"), product_id=pid, path="brief.md"),
        lambda: fresh.files.list(principal=principal("mallory"), product_id=pid),
        lambda: write(service, pid, principal=principal("reader"), expected_version=1),
    ]:
        with pytest.raises(CompanyError):
            operation()
    other = create(service, "Other")
    scoped = replace(principal(), agent_id="agent:pm", product_id=other["id"])
    with pytest.raises(CompanyError):
        fresh.files.read(principal=scoped, product_id=pid, path="brief.md")
    assert fresh.files.list(principal=principal(), product_id=other["id"])["data"] == []


def test_file_conflict_retry_revocation_and_audit_are_atomic(setup, monkeypatch):
    db, _, service = setup
    pid = create(service)["id"]
    key = str(uuid4())
    first = write(service, pid, idempotency_key=key)
    assert write(service, pid, idempotency_key=key) == first
    with pytest.raises(CompanyError, match="another write"):
        write(service, pid, idempotency_key=key, expected_version=1)

    def update(_):
        try:
            return write(service, pid, expected_version=1)["version"]
        except CompanyError as exc:
            return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update, range(2))) == [2, 412]
    original = service._insert

    def fail(conn, table, values):
        if table == "activity":
            raise RuntimeError("audit unavailable")
        return original(conn, table, values)

    monkeypatch.setattr(service, "_insert", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        write(service, pid, expected_version=2)
    assert service.files.read(principal=principal(), product_id=pid, path="brief.md")["version"] == 2
    setup[1].set_disabled("alice", True)
    with pytest.raises(CompanyError):
        write(service, pid, idempotency_key=key)


def test_global_files_paths_limits_and_async(setup):
    service = setup[2]
    write(service)
    assert asyncio.run(service.files.aread(principal=principal(), path="brief.md"))["version"] == 1
    assert asyncio.run(service.files.alist(principal=principal()))["data"][0]["path"] == "brief.md"
    pid = create(service)["id"]
    asyncio.run(service.files.awrite(product_id=pid, path="note.md", content="facts", expected_version=0, **mutation()))
    for path in ("../escape", "/absolute", "tasks/not-an-id/file.md"):
        with pytest.raises(CompanyError):
            service.files.write(product_id=pid, path=path, content="x", expected_version=0, **mutation())
    with pytest.raises(CompanyError):
        service.files.write(product_id=pid, path="large.md", content="é" * 600000, expected_version=0, **mutation())
    scoped = replace(principal(), agent_id="agent:pm", product_id=pid)
    with pytest.raises(CompanyError):
        service.files.read(principal=scoped, path="brief.md")


def test_files_http_and_tools_use_the_same_permissions(setup):
    db, users, _ = setup
    os = AgentOS(
        id="company-test",
        db=db,
        company=CompanyConfig(),
        user_directory=users,
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
    )
    pid = create(os.company)["id"]
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token()
        url = f"/company/v1/files/content?product_id={pid}"
        response = client.put(
            url,
            json={"path": "brief.md", "content": "  exact\n", "expected_version": 0},
            headers={"Idempotency-Key": "file-http"},
        )
        assert response.status_code == 200, response.text
        assert client.get(url + "&path=brief.md").json()["content"] == "  exact\n"
        client.headers["Authorization"] = "Bearer " + token(who="mallory")
        assert client.get(url + "&path=brief.md").status_code == 404
    from types import SimpleNamespace

    from agno.os.company.context import CompanyContext, current_company
    from agno.run import RunContext
    from agno.tools.company import CompanyTools

    tools = CompanyTools()
    ctx = current_company.set(CompanyContext(os.company, principal(), pid))
    try:
        result = tools.read_file(
            "brief.md", SimpleNamespace(id="pm"), pid, RunContext(user_id="alice", run_id="r", session_id="s")
        )
        assert result["content"] == "  exact\n"
    finally:
        current_company.reset(ctx)
    with pytest.raises(CompanyError):
        tools.read_file("brief.md", SimpleNamespace(id="pm"), pid)


def test_dispatch_pins_files_and_revision_reuses_original_context(setup):
    import json

    from test_execution import caller, make_work, runtime_os
    from test_progression import accept_ready

    os, _ = runtime_os(setup)
    service = os.company
    product, task = make_work(service, project=True)
    write(service, product["id"])
    task = accept_ready(service, task)
    runtime = service._runtime
    row = runtime._reserve(caller(), task["id"], task["version"], "snapshot", "", "manual")
    original = row["payload"]["company_files"]
    assert original["product/brief.md"]["content"] == "  Useful facts\n"
    write(service, product["id"], expected_version=1)
    assert json.loads(row["payload"]["input"])["company_files"] == original
    runtime._settle(row, "completed")
    with service._engine.connect() as conn:
        saved = conn.execute(
            text("SELECT payload FROM agno_company.task_runs WHERE id=:id"), {"id": row["id"]}
        ).scalar_one()
    assert saved["company_files"] == original

    current = service.get_task(principal=caller(), task_id=task["id"])
    current = transition(service, current, "in_progress", reason="Please revise")
    revision = runtime._reserve(caller(), task["id"], current["version"], "revision", "Revise this", "manual")
    assert revision["payload"]["company_files"] == original


def test_run_output_import_is_atomic_and_replay_does_not_overwrite(setup, monkeypatch):
    from types import SimpleNamespace

    from test_execution import caller, make_work, runtime_os
    from test_progression import accept_ready

    os, worker = runtime_os(setup)
    service = os.company
    product, task = make_work(service, project=True)
    task = accept_ready(service, task)
    row = service._runtime._reserve(caller(), task["id"], task["version"], "output", "", "manual")
    monkeypatch.setattr(
        worker, "get_run_output", lambda **kwargs: SimpleNamespace(content="Verified checks", metadata={})
    )
    original = service._insert

    def fail(conn, table, values):
        if table == "activity":
            raise RuntimeError("audit unavailable")
        return original(conn, table, values)

    monkeypatch.setattr(service, "_insert", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        service._runtime._settle(row, "completed")
    path = f"tasks/{task['id']}/results/{row['id']}.md"
    with pytest.raises(CompanyError):
        service.files.read(principal=caller(), product_id=product["id"], path=path)
    with service._engine.connect() as conn:
        assert not conn.execute(
            text("SELECT released FROM agno_company.task_runs WHERE id=:id"), {"id": row["id"]}
        ).scalar_one()
    monkeypatch.setattr(service, "_insert", original)
    service._runtime._settle(row, "completed")
    service._runtime._settle(row, "completed")
    saved = service.files.read(principal=caller(), product_id=product["id"], path=path)
    assert saved["content"] == "Verified checks" and saved["version"] == 1
    with pytest.raises(CompanyError, match="runtime"):
        service.files.write(product_id=product["id"], path=path, content="fabricated", expected_version=1, **mutation())


def test_output_quota_keeps_run_reconcilable(setup, monkeypatch):
    from types import SimpleNamespace

    from test_execution import caller, make_work, runtime_os
    from test_progression import accept_ready

    os, worker = runtime_os(setup)
    service = os.company
    product, task = make_work(service, project=True)
    task = accept_ready(service, task)
    row = service._runtime._reserve(caller(), task["id"], task["version"], "quota", "", "manual")
    monkeypatch.setattr(worker, "get_run_output", lambda **kwargs: SimpleNamespace(content="output", metadata={}))
    store = service.files._store

    def limited(product_id):
        result = store(product_id)
        result.max_namespace_bytes = 1
        return result

    monkeypatch.setattr(service.files, "_store", limited)
    with pytest.raises(CompanyError, match="space"):
        service._runtime._settle(row, "completed")
    with service._engine.connect() as conn:
        assert not conn.execute(
            text("SELECT released FROM agno_company.task_runs WHERE id=:id"), {"id": row["id"]}
        ).scalar_one()
    monkeypatch.setattr(service.files, "_store", store)
    service._runtime._settle(row, "completed")
    assert service.get_task(principal=caller(), task_id=task["id"])["status"] == "in_review"


def test_run_history_does_not_consume_the_next_snapshot_budget(setup):
    from test_execution import caller, make_work, runtime_os

    os, _ = runtime_os(setup)
    service = os.company
    product, task = make_work(service)
    write(service, product["id"])
    with service._engine.begin() as conn:
        service.files._backend._write_on(
            conn,
            service.files._store(product["id"]).namespace,
            f"tasks/{task['id']}/results/previous.md",
            "x" * 300_000,
        )
    with service._transaction(caller()) as conn:
        snapshot = service.files._snapshot(conn, caller(), product["id"], task["id"], None)
    assert list(snapshot) == ["product/brief.md"]
