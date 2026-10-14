import os

import pytest

from agno.db.postgres import PostgresDb
from agno.os import CompanyConfig, UserDirectory
from agno.os.company.migrations import migrate
from agno.os.company.service import CompanyService


@pytest.fixture
def setup():
    url = os.getenv("COMPANY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set COMPANY_TEST_DATABASE_URL to a disposable PostgreSQL database")
    db = PostgresDb(db_url=url)
    with db.db_engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA IF EXISTS agno_company CASCADE")
    migrate(db)
    users = UserDirectory()
    for who in ("alice", "bob", "reader", "mallory"):
        users.upsert(who)
    service = CompanyService(CompanyConfig(db=db), users)
    return db, users, service
