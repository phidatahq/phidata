"""Model-free Product CRUD through the authenticated Company API."""

import os
import secrets

from agno.db.postgres import PostgresDb
from agno.os import AgentOS, Authorization, CompanyConfig, create_dev_token
from fastapi.testclient import TestClient

# A disposable PostgreSQL database is recommended for this example.
db = PostgresDb(
    db_url=os.environ["COMPANY_DATABASE_URL"], db_schema="company_products_demo"
)
secret = secrets.token_urlsafe(32)
agent_os = AgentOS(
    id="company-products-demo",
    db=db,
    company=CompanyConfig(),
    authorization=Authorization(verification_keys=[secret], algorithm="HS256"),
    auto_provision_dbs=False,
    tracing=False,
    telemetry=False,
)
assert agent_os.company is not None
# Explicit deployment step, never performed by get_app() or application startup.
agent_os.company.initialize_schema()
token = create_dev_token(
    "alice",
    secret=secret,
    audience=agent_os.id,
    scopes=["company:read", "company:write", "company:delete"],
)
headers = {"Authorization": "Bearer " + token}
with TestClient(agent_os.get_app()) as client:
    created = client.post(
        "/company/v1/products",
        headers=headers,
        json={"name": "Documentation", "purpose": "Keep guides useful and current"},
    )
    assert created.status_code == 201, created.text
    product = created.json()
    url = "/company/v1/products/" + product["id"]
    assert product["owner_id"] == "alice"
    assert client.get(url, headers=headers).json() == product
    assert product in client.get("/company/v1/products", headers=headers).json()
    updated = client.patch(
        url,
        headers=headers,
        json={"name": "Developer documentation", "expected_version": 1},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    stale = client.patch(
        url, headers=headers, json={"name": "Stale edit", "expected_version": 1}
    )
    assert stale.status_code == 409
    assert (
        client.delete(url, params={"expected_version": 2}, headers=headers).status_code
        == 204
    )
    assert client.get(url, headers=headers).status_code == 404
print(
    "PASS: authenticated Product CRUD, scoped listing, and version conflicts without a model"
)
