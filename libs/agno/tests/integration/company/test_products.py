"""Company contract exercised against disposable SQL databases, without a model."""

import asyncio
import inspect
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from agno.db.base import AsyncBaseDb
from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.db.schemas.company import CompanyConflict, CompanyForbidden, CompanyNotFound
from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from agno.os.company.async_service import AsyncCompanyService
from agno.os.company.service import CompanyService


async def call(fn, *args, **kwargs):
    result = fn(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


@pytest_asyncio.fixture(params=["sqlite", "async_sqlite", "postgres", "async_postgres"])
async def db(request, tmp_path):
    kind = request.param
    suffix = uuid4().hex[:12]
    tables = dict(products_table="products_" + suffix, members_table="members_" + suffix)
    if "postgres" in kind:
        url = os.getenv("COMPANY_TEST_POSTGRES_URL")
        if not url:
            pytest.skip("Set COMPANY_TEST_POSTGRES_URL to a disposable PostgreSQL database")
        cls = AsyncPostgresDb if kind.startswith("async") else PostgresDb
        if kind.startswith("async"):
            url = url.replace("postgresql+psycopg://", "postgresql+psycopg_async://").replace(
                "postgresql+psycopg2://", "postgresql+asyncpg://"
            )
        database = cls(db_url=url, db_schema="company_" + suffix, **tables)
    else:
        cls = AsyncSqliteDb if kind.startswith("async") else SqliteDb
        database = cls(db_file=str(tmp_path / "company.db"), **tables)
    yield database
    if "postgres" in kind:
        if isinstance(database, AsyncBaseDb):
            async with database.db_engine.begin() as conn:
                await conn.execute(text('DROP SCHEMA IF EXISTS "' + database.db_schema + '" CASCADE'))
        else:
            with database.db_engine.begin() as conn:
                conn.execute(text('DROP SCHEMA IF EXISTS "' + database.db_schema + '" CASCADE'))
    await call(database.close)


def service(db):
    return AsyncCompanyService(db) if isinstance(db, AsyncBaseDb) else CompanyService(db)


@pytest.mark.asyncio
async def test_product_lifecycle_access_and_versions(db):
    s = service(db)
    p = await call(s.create_product, "alice", "Documentation", "Maintain docs")
    pid = p["id"]
    assert p["version"] == 1 and p["owner_id"] == "alice"
    assert (await call(s.list_members, "alice", pid))[0]["role"] == "owner"
    await call(s.add_member, "alice", pid, "bob")
    assert (await call(s.get_product, "bob", pid))["id"] == pid
    with pytest.raises(CompanyNotFound):
        await call(s.get_product, "outsider", pid)
    for method, args in [
        (s.add_member, ("bob", pid, "charlie")),
        (s.remove_member, ("bob", pid, "alice")),
        (s.archive_product, ("bob", pid, 1)),
        (s.restore_product, ("bob", pid, 1)),
        (s.update_product, ("bob", pid, 1)),
    ]:
        with pytest.raises(CompanyForbidden):
            await call(method, *args)
    p = await call(s.update_product, "alice", pid, 1, name="Docs")
    assert p["version"] == 2
    with pytest.raises(CompanyConflict):
        await call(s.archive_product, "alice", pid, 1)
    p = await call(s.archive_product, "alice", pid, 2)
    assert p["status"] == "archived"
    p = await call(s.restore_product, "alice", pid, p["version"])
    assert p["status"] == "active"
    await call(s.remove_member, "alice", pid, "bob")
    with pytest.raises(CompanyNotFound):
        await call(s.list_members, "bob", pid)
    assert await call(s.list_products, "bob") == []


@pytest.mark.asyncio
async def test_owner_reassignment_and_last_owner(db):
    s = service(db)
    p = await call(s.create_product, "alice", "SDK")
    pid = p["id"]
    for fn, args in [(s.remove_member, ("alice", pid, "alice")), (s.add_member, ("alice", pid, "alice", "member"))]:
        with pytest.raises(CompanyConflict):
            await call(fn, *args)
    await call(s.add_member, "alice", pid, "bob", "owner")
    await call(s.add_member, "alice", pid, "alice", "member")
    assert (await call(s.get_product, "bob", pid))["owner_id"] == "bob"
    with pytest.raises(CompanyForbidden):
        await call(s.add_member, "alice", pid, "eve")
    await call(s.add_member, "bob", pid, "alice", "owner")
    await call(s.remove_member, "bob", pid, "bob")
    assert (await call(s.get_product, "alice", pid))["owner_id"] == "alice"
    with pytest.raises(CompanyNotFound):
        await call(s.archive_product, "bob", pid, 1)


@pytest.mark.asyncio
async def test_membership_filter_precedes_pagination(db):
    s = service(db)
    for i in range(4):
        await call(s.create_product, "hidden", "Hidden " + str(i))
    visible = []
    for i in range(3):
        p = await call(s.create_product, "alice", "Visible " + str(i))
        visible.append(p["id"])
    actual = []
    for page in range(1, 4):
        rows = await call(s.list_products, "alice", limit=1, page=page)
        assert len(rows) == 1
        actual.append(rows[0]["id"])
    assert set(actual) == set(visible)
    assert await call(s.list_products, "hidden", status="archived") == []


@pytest.mark.asyncio
async def test_atomic_creation_and_migration_registration(db):
    s = service(db)
    p = await call(s.create_product, "owner", "Product")
    assert await call(db.table_exists, db.products_table_name)
    assert await call(db.table_exists, db.members_table_name)
    for name in [db.products_table_name, db.members_table_name]:
        assert await call(db.get_latest_schema_version, name) == "3.0.0"
    # Duplicate owner membership forces the second INSERT to fail; the Product
    # INSERT must roll back with it, leaving no orphaned Product.
    members = await call(db._get_table, "members", create_table_if_not_found=True)
    row = dict(product_id="rollback", user_id="owner", role="owner", created_at=1, updated_at=1)
    if isinstance(db, AsyncBaseDb):
        async with db.db_engine.begin() as conn:
            await conn.execute(members.insert().values(**row))
    else:
        with db.db_engine.begin() as conn:
            conn.execute(members.insert().values(**row))
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await call(db.create_product, {**p, "id": "rollback"})
    assert await call(db.get_product, "rollback") is None
    from agno.db.migrations.manager import MigrationManager

    await MigrationManager(db).up(table_type="products")
    await MigrationManager(db).up(table_type="members")
    clone = type(db).from_dict(db.to_dict())
    assert clone.products_table_name == db.products_table_name
    assert clone.members_table_name == db.members_table_name
    assert (await call(clone.get_product, p["id"]))["name"] == "Product"
    await call(clone.close)


@pytest.mark.asyncio
async def test_concurrent_updates_and_owner_removal(db):
    s = service(db)
    p = await call(s.create_product, "alice", "Concurrency")
    pid = p["id"]
    await call(s.add_member, "alice", pid, "bob", "owner")
    # Separate adapter instances represent independent application processes.
    other = type(db).from_dict(db.to_dict())
    s2 = service(other)

    async def run_pair(f1, a1, f2, a2):
        if isinstance(db, AsyncBaseDb):
            return await asyncio.gather(f1(*a1), f2(*a2), return_exceptions=True)
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(f1, *a1), pool.submit(f2, *a2)]
            results = []
            for future in futures:
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append(exc)
            return results

    results = await run_pair(s.archive_product, ("alice", pid, 1), s2.archive_product, ("bob", pid, 1))
    assert sum(isinstance(r, CompanyConflict) for r in results) == 1, results
    results = await run_pair(s.remove_member, ("alice", pid, "bob"), s2.remove_member, ("bob", pid, "alice"))
    assert sum(isinstance(r, (CompanyNotFound, CompanyConflict)) for r in results) == 1, results
    owners = [m for m in await call(db.list_members, pid) if m["role"] == "owner"]
    assert len(owners) == 1
    assert (await call(db.get_product, pid))["owner_id"] == owners[0]["user_id"]
    await call(other.close)


@pytest.mark.asyncio
async def test_storage_rechecks_revoked_actor(db):
    s = service(db)
    p = await call(s.create_product, "alice", "Revocation")
    pid = p["id"]
    await call(s.add_member, "alice", pid, "bob", "owner")
    await call(s.remove_member, "alice", pid, "bob")
    # Simulate revocation after the service check but before the storage write.
    with pytest.raises(CompanyNotFound):
        await call(db.update_product, pid, 1, actor_id="bob", name="Unauthorized")
    with pytest.raises(CompanyNotFound):
        await call(db.upsert_member, pid, "eve", "owner", actor_id="bob")


@pytest.mark.asyncio
@pytest.mark.parametrize("override", [False, True])
async def test_authenticated_http_on_each_adapter(db, tmp_path, override):
    from httpx import ASGITransport, AsyncClient

    from agno.os import AgentOS, CompanyConfig, create_dev_token
    from agno.os.config import AuthorizationConfig

    secret = "company-integration-secret-32-bytes"
    default_db = SqliteDb(db_file=str(tmp_path / "default.db")) if override else db
    app = AgentOS(
        db=default_db,
        company=CompanyConfig(db=db) if override else CompanyConfig(),
        telemetry=False,
        auto_provision_dbs=False,
        authorization=True,
        authorization_config=AuthorizationConfig(verification_keys=[secret], algorithm="HS256"),
    ).get_app()
    owner = {
        "Authorization": "Bearer " + create_dev_token("owner", secret=secret, scopes=["company:read", "company:write"])
    }
    outsider = {"Authorization": "Bearer " + create_dev_token("outsider", secret=secret, scopes=["agent_os:admin"])}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/company/v1/products", json={"name": "HTTP"}, headers=owner)
        assert response.status_code == 200, response.text
        path = "/company/v1/products/" + response.json()["id"]
        assert (await client.get(path, headers=outsider)).status_code == 404
        assert (await client.put(path + "/members/member", json={"role": "member"}, headers=owner)).status_code == 200
        assert len((await client.get(path + "/members", headers=owner)).json()["data"]) == 2
        assert (await client.post(path + "/archive", json={"expected_version": 1}, headers=owner)).status_code == 200
        assert (await client.post(path + "/restore", json={"expected_version": 1}, headers=owner)).status_code == 409
        assert (await client.post(path + "/restore", json={"expected_version": 2}, headers=owner)).status_code == 200

    if override:
        assert not default_db.table_exists(default_db.products_table_name)
        default_db.close()


@pytest.mark.asyncio
async def test_general_provisioning_leaves_company_disabled(db):
    from agno.db.migrations.manager import MigrationManager

    await call(db._create_all_tables)
    assert not await call(db.table_exists, db.products_table_name)
    assert not await call(db.table_exists, db.members_table_name)
    await MigrationManager(db).up(table_type="products")
    await MigrationManager(db).up(table_type="members")
    assert not await call(db.table_exists, db.products_table_name)
    assert not await call(db.table_exists, db.members_table_name)
