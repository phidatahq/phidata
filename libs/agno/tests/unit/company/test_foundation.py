"""Assembly and authenticated HTTP contract for opt-in Company."""

import asyncio
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from agno.db.base import AsyncBaseDb
from agno.db.in_memory import InMemoryDb
from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from agno.os import AgentOS, CompanyConfig, create_dev_token
from agno.os.config import AuthorizationConfig

KEY = "company-tests-only-secret-with-32-bytes"


def headers(user="alice", scopes=None):
    return {
        "Authorization": "Bearer "
        + create_dev_token(user, secret=KEY, scopes=scopes if scopes is not None else ["company:read", "company:write"])
    }


def make_os(db, **kwargs):
    return AgentOS(db=db, telemetry=False, auto_provision_dbs=False, **kwargs)


def test_config_resolution_and_rejection(tmp_path):
    default = SqliteDb(db_file=str(tmp_path / "default.db"))
    override = SqliteDb(db_file=str(tmp_path / "override.db"))
    config = CompanyConfig()
    assert make_os(default, company=config)._company_db is default
    assert config.db is None  # A reusable config is not mutated by assembly.
    os = make_os(default, company=CompanyConfig(db=override))
    assert os._company_db is override
    assert inspect(default.db_engine).get_table_names() == []
    assert inspect(override.db_engine).get_table_names() == []
    assert make_os(None, company=CompanyConfig(db=override))._company_db is override
    with pytest.raises(ValueError, match="Company requires"):
        make_os(None, company=CompanyConfig())
    with pytest.raises(ValueError, match="InMemoryDb"):
        make_os(InMemoryDb(), company=CompanyConfig())
    with pytest.raises(TypeError, match="CompanyConfig"):
        make_os(default, company=True)


def test_import_does_not_enable_company(tmp_path):
    script = """
from sqlalchemy import inspect
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
import sys
assert "agno.os.company" not in sys.modules
db = SqliteDb(db_url="sqlite:///:memory:")
a = AgentOS(db=db, telemetry=False, auto_provision_dbs=False)
before = a.get_app().openapi()["paths"]
tables = inspect(db.db_engine).get_table_names()
from agno.os import CompanyConfig
b = AgentOS(db=db, telemetry=False, auto_provision_dbs=False)
after = b.get_app().openapi()["paths"]
assert before == after
assert tables == inspect(db.db_engine).get_table_names()
assert not any("company" in path for path in after)
assert not a._scheduler_enabled and not b._scheduler_enabled
"""
    subprocess.run([sys.executable, "-c", script], check=True)


@pytest.mark.parametrize("async_db", [False, True])
def test_http_identity_scopes_access_and_conflicts(tmp_path, async_db):
    cls = AsyncSqliteDb if async_db else SqliteDb
    db = cls(db_file=str(tmp_path / "http.db"))
    os = make_os(
        db,
        company=CompanyConfig(),
        authorization=True,
        authorization_config=AuthorizationConfig(verification_keys=[KEY], algorithm="HS256"),
    )
    client = TestClient(os.get_app())
    base = "/company/v1/products"
    assert client.post(base, json={"name": "Docs"}).status_code == 401
    assert client.post(base, json={"name": "Docs"}, headers=headers(scopes=["company:read"])).status_code == 403
    assert client.post(base, json={"name": "Docs", "owner_id": "eve"}, headers=headers()).status_code == 422
    response = client.post(base, json={"name": "Docs"}, headers=headers())
    assert response.status_code == 200, response.text
    p = response.json()
    path = base + "/" + p["id"]
    assert client.get(path, headers=headers("outsider")).status_code == 404
    assert client.get(base, headers=headers("outsider")).json() == {"data": []}
    assert client.put(path + "/members/bob", json={"role": "member"}, headers=headers()).status_code == 200
    assert client.get(path, headers=headers("bob")).status_code == 200
    assert client.post(path + "/archive", json={"expected_version": 1}, headers=headers("bob")).status_code == 403
    assert client.delete(path + "/members/alice", headers=headers("bob")).status_code == 403
    assert client.delete(path + "/members/alice", headers=headers()).status_code == 409
    assert client.patch(path, json={"expected_version": 1, "name": "New"}, headers=headers()).status_code == 200
    assert client.post(path + "/archive", json={"expected_version": 1}, headers=headers()).status_code == 409
    assert client.post(path + "/archive", json={"expected_version": 2}, headers=headers()).status_code == 200
    assert client.post(path + "/restore", json={"expected_version": 3}, headers=headers()).status_code == 200
    assert client.delete(path + "/members/bob", headers=headers()).status_code == 204
    assert client.get(path, headers=headers("bob")).status_code == 404
    assert client.get(path, headers=headers(scopes=["company:write"])).status_code == 403
    assert (
        client.put(path + "/members/eve", json={"role": "owner"}, headers=headers(scopes=["company:read"])).status_code
        == 403
    )
    assert client.get(base + "?user_id=alice", headers=headers("outsider")).json() == {"data": []}
    if isinstance(db, AsyncBaseDb):
        asyncio.run(db.close())
    else:
        db.close()


def test_unauthenticated_query_identity_is_not_trusted(tmp_path):
    db = SqliteDb(db_file=str(tmp_path / "anonymous.db"))
    client = TestClient(make_os(db, company=CompanyConfig(), user_isolation=True).get_app())
    response = client.post("/company/v1/products?user_id=alice", json={"name": "Spoof"})
    assert response.status_code == 401
    assert not db.table_exists(db.products_table_name)


def test_service_methods_have_async_parity():
    import inspect as pyinspect

    from agno.os.company.async_service import AsyncCompanyService
    from agno.os.company.service import CompanyService

    for name, method in pyinspect.getmembers(CompanyService, pyinspect.isfunction):
        if not name.startswith("_"):
            other = getattr(AsyncCompanyService, name)
            assert pyinspect.iscoroutinefunction(other)
            assert pyinspect.signature(method) == pyinspect.signature(other)


@pytest.mark.asyncio
@pytest.mark.parametrize("override", [False, True])
async def test_resolved_database_shutdown(tmp_path, monkeypatch, override):
    db = SqliteDb(db_file=str(tmp_path / "default.db"))
    company_db = SqliteDb(db_file=str(tmp_path / "company.db")) if override else db
    os = make_os(db, company=CompanyConfig(db=company_db))
    os.get_app()
    calls = []
    monkeypatch.setattr(company_db, "close", lambda: calls.append("closed"))
    await os._close_databases()
    assert calls == ["closed"]


def test_database_override_routes_use_only_resolved_db(tmp_path):
    default = SqliteDb(db_file=str(tmp_path / "default.db"))
    override = SqliteDb(db_file=str(tmp_path / "override.db"))
    os = make_os(
        default,
        company=CompanyConfig(db=override),
        authorization=True,
        authorization_config=AuthorizationConfig(verification_keys=[KEY], algorithm="HS256"),
    )
    client = TestClient(os.get_app())
    response = client.post("/company/v1/products", json={"name": "Override"}, headers=headers())
    assert response.status_code == 200
    assert override.table_exists(override.products_table_name)
    assert not default.table_exists(default.products_table_name)


def test_sync_service_work_runs_off_event_loop(tmp_path, monkeypatch):
    import threading

    from agno.os.company.service import CompanyService

    db = SqliteDb(db_file=str(tmp_path / "thread.db"))
    os = make_os(
        db,
        company=CompanyConfig(),
        authorization=True,
        authorization_config=AuthorizationConfig(verification_keys=[KEY], algorithm="HS256"),
    )
    original = CompanyService.create_product

    def create(self, *args, **kwargs):
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()
        assert threading.current_thread() is not threading.main_thread()
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CompanyService, "create_product", create)
    response = TestClient(os.get_app()).post("/company/v1/products", json={"name": "Thread"}, headers=headers())
    assert response.status_code == 200
