import os
from uuid import uuid4

import pytest
from sqlalchemy.schema import DropSchema

from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb


@pytest.fixture(params=["sqlite", "postgres"])
def company_db(request, tmp_path):
    if request.param == "sqlite":
        db = SqliteDb(db_file=str(tmp_path / "company.db"))
        yield db
        db.db_engine.dispose()
        return
    url = os.getenv("COMPANY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set COMPANY_TEST_DATABASE_URL to a disposable PostgreSQL database")
    db = PostgresDb(db_url=url, db_schema="company_test_" + uuid4().hex)
    yield db
    with db.db_engine.begin() as connection:
        connection.execute(DropSchema(db.db_schema, cascade=True, if_exists=True))
    db.db_engine.dispose()


@pytest.fixture
def auth_db(company_db, tmp_path):
    # Keep policy independently writable while a SQLite Product writer is locked.
    if isinstance(company_db, SqliteDb):
        db = SqliteDb(db_file=str(tmp_path / "auth.db"))
        yield db
        db.db_engine.dispose()
    else:
        yield company_db
