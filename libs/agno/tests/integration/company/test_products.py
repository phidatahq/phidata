"""Model-free SQLite and PostgreSQL proof of Product persistence, policy and concurrency."""

import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Column, MetaData, Table, Text, event, inspect

from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from agno.os import AgentOS, Authorization, CompanyConfig
from agno.os.authz.provider import AuthorizationContext, AuthorizationProvider
from agno.os.authz.scope_provider import ScopeAuthorizationProvider
from agno.os.company.schemas import ProductCreate, ProductUpdate
from agno.os.company.service import (
    CompanyAuthenticationError,
    CompanyService,
    ProductConflictError,
    ProductNotFoundError,
)
from agno.os.company.storage import CompanySchemaError
from agno.os.utils import flatten_routes
from agno.run.authorization import RunAuthorization, authorization_scope

SECRET = "company-products-test-secret-at-least-32-bytes"
SCOPES = ["company:read", "company:write", "company:delete"]
BODY = {"name": "Documentation", "purpose": "Keep guides useful"}
BASE = "/company/v1/products"


@contextmanager
def caller(subject="alice", scopes=None, provider=None, service_account=False):
    authority = RunAuthorization(
        provider or ScopeAuthorizationProvider(),
        AuthorizationContext(principal_id=subject, scopes=SCOPES if scopes is None else scopes),
        service_account=service_account,
        enforce_tools=False,
    )
    with authorization_scope(lambda: authority):
        yield authority


def headers(subject="alice", scopes=None, secret=SECRET, **claims):
    token = jwt.encode(
        {
            "sub": subject,
            "aud": "company-test",
            "exp": int(time.time()) + 600,
            "scopes": SCOPES if scopes is None else scopes,
            **claims,
        },
        secret,
        algorithm="HS256",
    )
    return {"Authorization": "Bearer " + token}


def make_os(db=None, *, config=None, authorization=None):
    return AgentOS(
        id="company-test",
        db=db,
        company=config if config is not None else CompanyConfig(),
        authorization=authorization
        or Authorization(verification_keys=[SECRET], algorithm="HS256", audience="company-test"),
        auto_provision_dbs=False,
        tracing=False,
        telemetry=False,
    )


@pytest.fixture
def service(company_db):
    service = CompanyService(company_db)
    service.initialize_schema()
    return service


def test_config_resolution_and_assembly_without_company_ddl(company_db):
    statements = []
    event.listen(company_db.db_engine, "before_cursor_execute", lambda c, cu, sql, *args: statements.append(sql))
    os_ = make_os(company_db)
    assert os_.company.db is company_db
    with TestClient(os_.get_app()) as client:
        assert BASE in client.get("/openapi.json").json()["paths"]
    assert not any(
        "company_" in sql.lower() and any(op in sql.upper() for op in ("CREATE", "ALTER", "INSERT"))
        for sql in statements
    )
    if isinstance(company_db, SqliteDb):
        assert not inspect(company_db.db_engine).get_table_names()
    else:
        assert not inspect(company_db.db_engine).has_schema(company_db.db_schema)
    assert os_.agents is None and os_.manager is None
    override = (
        PostgresDb(db_engine=company_db.db_engine, db_schema=getattr(company_db, "db_schema", None))
        if isinstance(company_db, PostgresDb)
        else SqliteDb(db_engine=company_db.db_engine)
    )
    os_override = make_os(SqliteDb(db_file=":memory:"), config=CompanyConfig(db=override))
    assert os_override.company.db is override
    os_override.db = company_db
    os_override.get_app()
    assert os_override.company.db is override
    assert make_os(config=CompanyConfig(db=company_db)).company.db is company_db


@pytest.mark.parametrize(
    "db", [None, AsyncSqliteDb(db_file=":memory:"), AsyncPostgresDb(db_url="postgresql+psycopg://unused/unused")]
)
def test_configuration_errors(db):
    with pytest.raises(ValueError, match="Company requires a database|synchronous PostgreSQL"):
        make_os(db)


def test_invalid_config_and_disguised_sqlite():
    from sqlalchemy import create_engine

    with pytest.raises(TypeError, match="CompanyConfig"):
        AgentOS(company=True)
    with pytest.raises(ValueError, match="synchronous PostgreSQL"):
        make_os(config=CompanyConfig(db=PostgresDb(db_engine=create_engine("sqlite://"))))


def test_disabled_company_does_not_import_or_initialize():
    script = """
import sys
from fastapi.testclient import TestClient
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
os_ = AgentOS(db=SqliteDb(db_file=":memory:"), auto_provision_dbs=False, telemetry=False, tracing=False)
with TestClient(os_.get_app()) as client:
    assert client.get("/company/v1/products").status_code == 404
    assert not any(p.startswith("/company") for p in client.get("/openapi.json").json()["paths"])
assert os_.company is None
assert not any(m.startswith("agno.os.company") for m in sys.modules)
"""
    result = subprocess.run([sys.executable, "-c", script], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr + result.stdout


def test_explicit_repeatable_init_and_persistence(company_db):
    service = CompanyService(company_db)
    with caller(), pytest.raises(CompanySchemaError, match="explicitly"):
        service.list_products()
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda _: CompanyService(company_db).initialize_schema(), range(2)))
    with caller():
        product = service.create_product(ProductCreate(**BODY))
        service.initialize_schema()
        assert CompanyService(company_db).get_product(product.id) == product
    with TestClient(make_os(company_db).get_app()) as client:
        assert client.get(BASE + "/" + product.id, headers=headers()).json() == product.model_dump(mode="json")
    tables = inspect(company_db.db_engine).get_table_names(schema=getattr(company_db, "db_schema", None))
    assert set(tables) == {"company_schema_version", "company_products"}


def test_initializer_preserves_existing_data_and_rejects_unknown_schema(company_db):
    schema = getattr(company_db, "db_schema", None)
    old = Table("company_old", MetaData(schema=schema), Column("value", Text))
    with company_db.db_engine.begin() as connection:
        if schema is not None:
            from sqlalchemy.schema import CreateSchema

            connection.execute(CreateSchema(schema))
        old.create(connection)
        connection.execute(old.insert().values(value="preserve"))
    with pytest.raises(CompanySchemaError, match="Unrecognized"):
        CompanyService(company_db).initialize_schema()
    with company_db.db_engine.connect() as connection:
        assert connection.execute(old.select()).scalar() == "preserve"
    assert inspect(company_db.db_engine).get_table_names(schema=schema) == ["company_old"]


def test_unsupported_version_does_not_mutate(service):
    with service.db.db_engine.begin() as connection:
        connection.execute(service._storage.version.update().values(version=99))
    with pytest.raises(CompanySchemaError, match="Unsupported"):
        service.initialize_schema()
    with caller(), pytest.raises(CompanySchemaError):
        service.create_product(ProductCreate(**BODY))


def test_http_crud_and_identity_and_ownership(service):
    with TestClient(make_os(service.db).get_app()) as client:
        alice = headers()
        assert client.get(BASE).status_code == 401
        assert (
            client.post(
                BASE, json=BODY, headers=headers(secret="forged-secret-that-is-also-at-least-32-bytes")
            ).status_code
            == 401
        )
        assert client.post(BASE, json={**BODY, "owner_id": "victim"}, headers=alice).status_code == 422
        assert client.post(BASE, json={**BODY, "user_id": "victim"}, headers=alice).status_code == 422
        forged = {
            **alice,
            "X-User-ID": "victim",
            "X-Agno-Run-Authorization": json.dumps({"context": {"principal_id": "victim"}}),
        }
        response = client.post(BASE + "?user_id=victim", json=BODY, headers=forged)
        assert response.status_code == 201, response.text
        product = response.json()
        assert product["owner_id"] == "alice" and product["version"] == 1
        url = BASE + "/" + product["id"]
        other = client.post(BASE, json=BODY, headers=headers("bob")).json()
        assert [p["id"] for p in client.get(BASE, headers=alice).json()] == [product["id"]]
        assert [p["id"] for p in client.get(BASE, headers=headers("bob")).json()] == [other["id"]]
        for outsider in (headers("bob"), headers("admin", ["agent_os:admin"])):
            assert client.get(url, headers=outsider).status_code == 404
            assert (
                client.patch(url, json={"name": "Stolen", "expected_version": 1}, headers=outsider).status_code == 404
            )
            assert client.delete(url + "?expected_version=1", headers=outsider).status_code == 404
        assert client.get(url, headers=alice).json() == product
        assert client.get(BASE, headers=headers(scopes=[])).status_code == 403
        assert client.get(BASE, headers=headers(None)).status_code == 401
        assert client.get(BASE, headers=headers("sa:robot")).status_code == 401
        assert client.patch(url, headers=alice, json={"owner_id": "bob", "expected_version": 1}).status_code == 422
        changed = client.patch(url, headers=alice, json={"purpose": "Better guides", "expected_version": 1})
        assert changed.status_code == 200 and changed.json()["version"] == 2
        assert client.patch(url, headers=alice, json={"name": "Stale", "expected_version": 1}).status_code == 409
        assert client.delete(url + "?expected_version=1", headers=alice).status_code == 409
        assert client.delete(url, headers=alice).status_code == 422
        assert client.delete(url + "?expected_version=2", headers=alice).status_code == 204
        assert client.get(url, headers=alice).status_code == 404
        assert client.get(BASE, headers=alice).json() == []


def test_no_auth_configuration_uses_shared_local_owner(service, monkeypatch):
    for variable in ("JWT_VERIFICATION_KEY", "JWT_JWKS_FILE", "JWT_JWKS_URL", "OS_SECURITY_KEY"):
        monkeypatch.delenv(variable, raising=False)
    os_ = AgentOS(db=service.db, company=CompanyConfig(), auto_provision_dbs=False, telemetry=False, tracing=False)
    app = os_.get_app()
    with TestClient(app) as client:
        response = client.post(BASE + "?user_id=alice", json=BODY, headers={"X-User-ID": "bob"})
        assert response.status_code == 201, response.text
        product = response.json()
        assert product["owner_id"] == "local"
        url = BASE + "/" + product["id"]
        assert client.get(BASE).json() == [product]
        assert client.get(url).json() == product
        os_.resync(app)
        assert client.patch(url, json={"name": "Local", "expected_version": 1}).json()["version"] == 2
        assert client.delete(url + "?expected_version=2").status_code == 204
    # The HTTP development context never leaks into unrelated Python calls.
    with pytest.raises(CompanyAuthenticationError):
        service.list_products()


def test_manually_installed_auth_exclusion_stays_closed(service, monkeypatch):
    from fastapi import FastAPI

    from agno.os.middleware.jwt import JWTMiddleware

    for variable in ("JWT_VERIFICATION_KEY", "JWT_JWKS_FILE", "OS_SECURITY_KEY"):
        monkeypatch.delenv(variable, raising=False)
    app = FastAPI()
    app.add_middleware(JWTMiddleware, verification_keys=[SECRET], algorithm="HS256", excluded_route_paths=[BASE])
    os_ = AgentOS(
        db=service.db, company=CompanyConfig(), base_app=app, auto_provision_dbs=False, telemetry=False, tracing=False
    )
    with TestClient(os_.get_app()) as client:
        assert client.post(BASE, json=BODY).status_code == 401


@pytest.mark.parametrize(
    "subject,service_account",
    [(None, False), ("", False), ("sa:robot", False), ("__scheduler__", False), ("alice", True)],
)
def test_service_rejects_nonhuman_identity(service, subject, service_account):
    with caller(subject, service_account=service_account), pytest.raises(CompanyAuthenticationError):
        service.create_product(ProductCreate(**BODY))


def test_service_checks_every_operation_and_scopes(service):
    with caller():
        product = service.create_product(ProductCreate(**BODY))
    operations = [
        lambda: service.create_product(ProductCreate(**BODY)),
        lambda: service.list_products(),
        lambda: service.get_product(product.id),
        lambda: service.update_product(product.id, ProductUpdate(name="New", expected_version=1)),
        lambda: service.delete_product(product.id, expected_version=1),
    ]
    for operation in operations:
        with pytest.raises(CompanyAuthenticationError):
            operation()
        with caller(scopes=[]), pytest.raises(PermissionError):
            operation()
    with caller("bob", ["agent_os:admin"]):
        assert service.list_products() == []
        for operation in operations[2:]:
            with pytest.raises(ProductNotFoundError):
                operation()


def test_live_managed_permission_revocation(service):
    authz = Authorization(db=service.db, verification_keys=[SECRET], algorithm="HS256", audience="company-test")
    authz.define_role("products", SCOPES)
    authz.define_role("none", [])
    authz.set_role("alice", "products")
    os_ = make_os(service.db, authorization=authz)
    with TestClient(os_.get_app()) as client:
        token = headers(scopes=["agent_os:admin"])
        product = client.post(BASE, json=BODY, headers=token).json()
        authz.set_role("alice", "none")
        for method, url, kwargs in [
            ("get", BASE, {}),
            ("get", BASE + "/" + product["id"], {}),
            ("post", BASE, {"json": BODY}),
            ("patch", BASE + "/" + product["id"], {"json": {"name": "Revoked", "expected_version": 1}}),
            ("delete", BASE + "/" + product["id"] + "?expected_version=1", {}),
        ]:
            assert getattr(client, method)(url, headers=token, **kwargs).status_code == 403
    with caller(provider=authz.provider), pytest.raises(PermissionError):
        service.update_product(product["id"], ProductUpdate(name="Retry", expected_version=1))
    with caller():
        assert service.get_product(product["id"]).version == 1


def test_concurrent_writers_and_delete_conflict(service):
    with caller():
        product = service.create_product(ProductCreate(**BODY))
    barrier = threading.Barrier(2)

    def update(name):
        with caller():
            barrier.wait(timeout=5)
            try:
                return service.update_product(product.id, ProductUpdate(name=name, expected_version=1))
            except ProductConflictError:
                return "conflict"

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(update, ["One", "Two"]))
    assert results.count("conflict") == 1
    with caller():
        current = service.get_product(product.id)
        assert current.version == 2 and current.name in ("One", "Two")
        with pytest.raises(ProductConflictError):
            service.delete_product(product.id, expected_version=1)


def test_policy_rechecked_after_lock_wait(service):
    class Revocable(ScopeAuthorizationProvider):
        allowed = True

        def authorize_route(self, ctx, required_scopes):
            return self.allowed and super().authorize_route(ctx, required_scopes)

    policy = Revocable()
    waiting = threading.Event()
    main_thread = threading.get_ident()

    def before_statement(connection, cursor, sql, *args):
        if ("FOR UPDATE" in sql or sql == "BEGIN IMMEDIATE") and threading.get_ident() != main_thread:
            waiting.set()

    event.listen(service.db.db_engine, "before_cursor_execute", before_statement)
    with caller():
        product = service.create_product(ProductCreate(**BODY))
    table = service._storage.products

    def update():
        with caller(provider=policy):
            return service.update_product(product.id, ProductUpdate(name="Revoked", expected_version=1))

    with ThreadPoolExecutor(1) as pool:
        with service._storage._write() as connection:
            connection.execute(table.select().where(table.c.id == product.id).with_for_update())
            future = pool.submit(update)
            assert waiting.wait(5)
            policy.allowed = False
        with pytest.raises(PermissionError):
            future.result(timeout=5)
    with caller():
        assert service.get_product(product.id).version == 1


@pytest.mark.asyncio
async def test_async_parity_and_nonblocking_database(company_db):
    service = CompanyService(company_db)
    await service.ainitialize_schema()
    await service.ainitialize_schema()
    event_loop_thread = threading.get_ident()
    db_threads = []
    event.listen(company_db.db_engine, "before_cursor_execute", lambda *args: db_threads.append(threading.get_ident()))
    with caller():
        product = await service.acreate_product(ProductCreate(**BODY))
        assert await service.aget_product(product.id) == service.get_product(product.id)
        assert await service.alist_products() == [product]
        changed = await service.aupdate_product(product.id, ProductUpdate(name="Async", expected_version=1))
        assert changed.version == 2
        with pytest.raises(ProductConflictError):
            await service.aupdate_product(product.id, ProductUpdate(name="Stale", expected_version=1))
        db_threads.clear()
        await service.aget_product(product.id)
        assert db_threads and event_loop_thread not in db_threads
        await service.adelete_product(product.id, expected_version=2)
        assert await service.alist_products() == []
    with pytest.raises(CompanyAuthenticationError):
        await service.alist_products()
    with caller(scopes=[]), pytest.raises(PermissionError):
        await service.acreate_product(ProductCreate(**BODY))


def test_custom_provider_deferral_does_not_grant_access(service):
    class Deferring(AuthorizationProvider):
        def check(self, ctx):
            return True

        def accessible_resource_ids(self, ctx):
            return {"*"}

    with caller(provider=Deferring()), pytest.raises(PermissionError):
        service.list_products()


@pytest.mark.parametrize(
    "body", [{"name": " ", "purpose": "x"}, {"name": "x", "purpose": ""}, {**BODY, "owner_id": "bob"}]
)
def test_create_validation(body):
    with pytest.raises(ValidationError):
        ProductCreate(**body)


@pytest.mark.parametrize(
    "body",
    [
        {"expected_version": 1},
        {"expected_version": 1, "name": None},
        {"expected_version": 0, "name": "x"},
        {"expected_version": True, "name": "x"},
    ],
)
def test_update_validation(body):
    with pytest.raises(ValidationError):
        ProductUpdate(**body)


def test_resync_reuses_resolved_company_and_preserves_routes(service):
    os_ = make_os(service.db)
    original_service = os_.company
    app = os_.get_app()
    with TestClient(app) as client:
        created = client.post(BASE, headers=headers(), json=BODY).json()
        os_.resync(app)
        os_.resync(app)
        assert os_.company is original_service
        assert client.get(BASE + "/" + created["id"], headers=headers()).json() == created
        assert (
            sum(
                getattr(route, "path", None) == BASE and "POST" in getattr(route, "methods", [])
                for route in flatten_routes(app.routes)
            )
            == 1
        )


def test_override_persists_only_to_company_database(company_db, tmp_path):
    from sqlalchemy.schema import DropSchema

    override = (
        PostgresDb(db_engine=company_db.db_engine, db_schema=company_db.db_schema + "_override")
        if isinstance(company_db, PostgresDb)
        else SqliteDb(db_file=str(tmp_path / "override.db"))
    )
    try:
        os_ = make_os(company_db, config=CompanyConfig(db=override))
        os_.company.initialize_schema()
        with caller():
            product = os_.company.create_product(ProductCreate(**BODY))
            assert CompanyService(override).get_product(product.id) == product
        if isinstance(company_db, SqliteDb):
            assert not inspect(company_db.db_engine).get_table_names()
        else:
            assert not inspect(company_db.db_engine).has_schema(company_db.db_schema)
    finally:
        if isinstance(override, PostgresDb):
            with override.db_engine.begin() as connection:
                connection.execute(DropSchema(override.db_schema, cascade=True, if_exists=True))
        else:
            override.db_engine.dispose()


def test_uninitialized_http_returns_actionable_error(company_db):
    with TestClient(make_os(company_db).get_app()) as client:
        response = client.get(BASE, headers=headers())
        assert response.status_code == 503
        assert "initialize_schema" in response.text
    if isinstance(company_db, SqliteDb):
        assert not inspect(company_db.db_engine).get_table_names()
    else:
        assert not inspect(company_db.db_engine).has_schema(company_db.db_schema)


def test_pagination_filters_owner_before_limiting(service):
    with caller("bob"):
        service.create_product(ProductCreate(**BODY))
    with caller():
        first = service.create_product(ProductCreate(**BODY))
        second = service.create_product(ProductCreate(**BODY))
        pages = service.list_products(limit=1) + service.list_products(limit=1, offset=1)
        assert [p.id for p in pages] == sorted([first.id, second.id])
        assert service.list_products(limit=1, offset=2) == []
        for limit, offset in [(0, 0), (101, 0), (1, -1)]:
            with pytest.raises(ValueError):
                service.list_products(limit=limit, offset=offset)


@pytest.mark.asyncio
async def test_async_denials_and_ownership_match_sync(service):
    with caller():
        product = await service.acreate_product(ProductCreate(**BODY))
    operations = [
        lambda: service.acreate_product(ProductCreate(**BODY)),
        lambda: service.alist_products(),
        lambda: service.aget_product(product.id),
        lambda: service.aupdate_product(product.id, ProductUpdate(name="No", expected_version=1)),
        lambda: service.adelete_product(product.id, expected_version=1),
    ]
    for operation in operations:
        with pytest.raises(CompanyAuthenticationError):
            await operation()
        with caller(scopes=[]), pytest.raises(PermissionError):
            await operation()
    with caller("bob"):
        assert await service.alist_products() == []
        for operation in operations[2:]:
            with pytest.raises(ProductNotFoundError):
                await operation()


def test_authentication_route_exclusion_does_not_bypass_service(service):
    auth = Authorization(verification_keys=[SECRET], algorithm="HS256", excluded_route_paths=[BASE])
    with TestClient(make_os(service.db, authorization=auth).get_app()) as client:
        assert client.post(BASE, json=BODY, headers={"X-User-ID": "alice"}).status_code == 401


def test_http_role_revocation_during_product_lock_wait(service, auth_db):
    authz = Authorization(db=auth_db, verification_keys=[SECRET], algorithm="HS256", audience="company-test")
    authz.define_role("products", SCOPES)
    authz.define_role("none", [])
    authz.set_role("alice", "products")
    waiting = threading.Event()
    main_thread = threading.get_ident()

    def before_statement(connection, cursor, sql, *args):
        if (
            ("FOR UPDATE" in sql and "company_products" in sql) or sql == "BEGIN IMMEDIATE"
        ) and threading.get_ident() != main_thread:
            waiting.set()

    event.listen(service.db.db_engine, "before_cursor_execute", before_statement)
    with TestClient(make_os(service.db, authorization=authz).get_app()) as client:
        product = client.post(BASE, headers=headers(), json=BODY).json()
        table = service._storage.products
        with ThreadPoolExecutor(1) as pool:
            with service._storage._write() as connection:
                connection.execute(table.select().where(table.c.id == product["id"]).with_for_update())
                response = pool.submit(
                    client.patch,
                    BASE + "/" + product["id"],
                    headers=headers(),
                    json={"name": "Revoked while waiting", "expected_version": 1},
                )
                assert waiting.wait(5)
                # A different request/process changes policy while the mutation is blocked.
                authz.set_role("alice", "none")
            assert response.result(timeout=5).status_code == 403
    with caller():
        assert service.get_product(product["id"]).version == 1


def test_failed_initialization_rolls_back_all_company_tables(company_db):
    def fail_marker(connection, cursor, sql, *args):
        if sql.startswith("INSERT INTO") and "company_schema_version" in sql:
            raise RuntimeError("injected initialization failure")

    event.listen(company_db.db_engine, "before_cursor_execute", fail_marker)
    service = CompanyService(company_db)
    with pytest.raises(RuntimeError, match="injected"):
        service.initialize_schema()
    event.remove(company_db.db_engine, "before_cursor_execute", fail_marker)
    inspector = inspect(company_db.db_engine)
    schema = service._storage.schema
    assert not inspector.has_table("company_products", schema=schema)
    assert not inspector.has_table("company_schema_version", schema=schema)
    service.initialize_schema()
    with caller():
        created = service.create_product(ProductCreate(**BODY))
    company_db.db_engine.dispose()
    with caller():
        assert CompanyService(company_db).get_product(created.id) == created


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///:memory:", "sqlite:///file:company?mode=memory&uri=true"])
def test_in_memory_sqlite_reports_thread_storage_requirement(url):
    with pytest.raises(ValueError, match="file-backed SQLite"):
        CompanyService(SqliteDb(db_url=url))
