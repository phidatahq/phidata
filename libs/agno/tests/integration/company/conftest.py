import os
from uuid import uuid4

import pytest
from sqlalchemy.schema import DropSchema

from agno.db.postgres import PostgresDb


@pytest.fixture
def company_db():
    url = os.getenv("COMPANY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set COMPANY_TEST_DATABASE_URL to a disposable PostgreSQL database")
    db = PostgresDb(db_url=url, db_schema="company_test_" + uuid4().hex)
    yield db
    with db.db_engine.begin() as connection:
        connection.execute(DropSchema(db.db_schema, cascade=True, if_exists=True))
    db.db_engine.dispose()
