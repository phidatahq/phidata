"""Persist shared Product context using Company permissions and file versions.

Run against a migrated development database with COMPANY_DATABASE_URL set.
The local principal represents a trusted operator; HTTP callers use verified JWTs.
"""

from os import environ
from uuid import uuid4

import agno
from agno.db.postgres import PostgresDb
from agno.os import CompanyConfig, UserDirectory
from agno.os.authz.scope_provider import ScopeAuthorizationProvider
from agno.os.company.policy import Principal
from agno.os.company.schemas import ProductCreate
from agno.os.company.service import CompanyService


def main() -> None:
    print(agno.__file__)
    db = PostgresDb(db_url=environ["COMPANY_DATABASE_URL"])
    users = UserDirectory()
    users.upsert("alex")
    service = CompanyService(CompanyConfig(db=db), users)
    principal = Principal(
        "alex",
        ScopeAuthorizationProvider(),
        ("company:manage", "company_products:read", "company_products:write"),
    )
    request = {"principal": principal, "request_id": str(uuid4())}
    product = service.create_product(
        data=ProductCreate(name="Documentation"),
        idempotency_key="files-product",
        **request,
    )
    file = service.files.write(
        product_id=product["id"],
        path="brief.md",
        content="Keep documentation aligned with released SDK behavior.\n",
        expected_version=0,
        idempotency_key="files-brief",
        **request,
    )
    print(file)
    # A new service instance reads the same shared files.
    fresh = CompanyService(CompanyConfig(db=db), users)
    print(
        fresh.files.read(principal=principal, product_id=product["id"], path="brief.md")
    )


if __name__ == "__main__":
    main()
