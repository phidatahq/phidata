"""Create and review one Project Task through the same service used by HTTP.

Uses a trusted local operator context, not a model or caller-supplied identity.
Run against a migrated development database with COMPANY_DATABASE_URL set.
"""

from os import environ
from uuid import uuid4

from agno.db.postgres import PostgresDb
from agno.os import CompanyConfig, UserDirectory
from agno.os.authz.scope_provider import ScopeAuthorizationProvider
from agno.os.company.policy import Principal
from agno.os.company.schemas import ProductCreate, ProjectCreate, TaskCreate, Transition
from agno.os.company.service import CompanyService


def main() -> None:
    db = PostgresDb(db_url=environ["COMPANY_DATABASE_URL"])
    users = UserDirectory(db=db, auto_provision=False)
    # Explicit operator bootstrap of a known human; no model writes or tokens.
    users.upsert("human:alex", name="Alex")
    principal = Principal(
        "human:alex",
        ScopeAuthorizationProvider(),
        (
            "company:manage",
            "company_products:read",
            "company_products:write",
            "company_products:review",
            "company_products:manage",
        ),
    )
    service = CompanyService(CompanyConfig(db=db), users)
    product = service.create_product(
        principal=principal,
        request_id=str(uuid4()),
        idempotency_key="manual-website",
        data=ProductCreate(
            name="Website",
            instructions="Help people use the product",
            owner_id=principal.id,
        ),
    )
    project = service.create_project(
        principal=principal,
        product_id=product["id"],
        request_id=str(uuid4()),
        idempotency_key="manual-onboarding",
        data=ProjectCreate(
            title="Improve onboarding",
            instructions="A clean installation succeeds",
            owner_id=principal.id,
        ),
    )
    task = service.create_task(
        principal=principal,
        product_id=product["id"],
        request_id=str(uuid4()),
        idempotency_key="manual-guide",
        data=TaskCreate(
            project_id=project["id"],
            title="Correct the setup guide",
            instructions="Follow the documented steps in a clean environment",
            accountable_owner_id=principal.id,
        ),
    )
    for status in ("ready", "in_progress", "in_review", "done"):
        task = service.transition_task(
            principal=principal,
            task_id=task["id"],
            version=task["version"],
            request_id=str(uuid4()),
            idempotency_key="manual-guide-" + status,
            data=Transition(
                to_status=status,
                reason="Model-free demonstration of human review"
                if status == "done"
                else "",
                acceptance_check="Demonstration only: an operator records the acceptance check here"
                if status == "done"
                else "",
            ),
        )
    print(service.get_project(principal=principal, project_id=project["id"])["counts"])
    print(task["status"])


if __name__ == "__main__":
    main()
