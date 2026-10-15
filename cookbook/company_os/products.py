"""Create, read, update, and delete Products without a model or auth setup."""

import os

from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, CompanyConfig
from fastapi.testclient import TestClient

# SQLite works out of the box. Set COMPANY_DATABASE_URL to try PostgreSQL.
database_url = os.getenv("COMPANY_DATABASE_URL")
db = (
    PostgresDb(db_url=database_url, db_schema="company_products_demo")
    if database_url
    else SqliteDb(db_file="tmp/company_products.db")
)
agent_os = AgentOS(
    id="company-products-demo",
    db=db,
    company=CompanyConfig(),
    auto_provision_dbs=False,
    tracing=False,
    telemetry=False,
)
assert agent_os.company is not None
# Explicit deployment step, never performed by get_app() or application startup.
agent_os.company.initialize_schema()
with TestClient(agent_os.get_app()) as client:
    created = client.post(
        "/company/v1/products",
        json={"name": "Documentation", "purpose": "Keep guides useful and current"},
    )
    assert created.status_code == 201, created.text
    product = created.json()
    url = "/company/v1/products/" + product["id"]
    assert product["owner_id"] == "local"
    assert client.get(url).json() == product
    assert product in client.get("/company/v1/products").json()
    updated = client.patch(
        url,
        json={"name": "Developer documentation", "expected_version": 1},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    stale = client.patch(url, json={"name": "Stale edit", "expected_version": 1})
    assert stale.status_code == 409
    assert client.delete(url, params={"expected_version": 2}).status_code == 204
    assert client.get(url).status_code == 404
print("PASS: Product CRUD and version conflicts without a model or auth setup")
