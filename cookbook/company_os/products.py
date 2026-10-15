"""Create and manage Products with SQLite, without a model or API key."""

from pathlib import Path
from tempfile import TemporaryDirectory

from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, CompanyConfig
from agno.os.company.service import CompanyService


def main() -> None:
    # Use a disposable file so the example is repeatable and shares one database
    # across threads. Use a persistent path in an application.
    with TemporaryDirectory(prefix="company-products-") as directory:
        db = SqliteDb(db_file=str(Path(directory) / "company.db"))
        agent_os = AgentOS(db=db, company=CompanyConfig(), telemetry=False)
        service = CompanyService(db)

        # A trusted application supplies the authenticated caller's identity.
        # HTTP routes derive it from AgentOS authentication instead.
        product = service.create_product(
            "alice", "Documentation", "Keep documentation accurate"
        )
        service.add_member("alice", product["id"], "bob")
        assert service.list_products("alice")[0]["id"] == product["id"]
        assert service.list_products("bob")[0]["id"] == product["id"]
        assert service.list_products("outsider") == []
        print("Owner and member can see the Product; outsiders cannot.")

        product = service.archive_product("alice", product["id"], product["version"])
        assert product["status"] == "archived"
        product = service.restore_product("alice", product["id"], product["version"])
        assert product["status"] == "active"
        assert product["version"] == 3
        print("Product archived and restored with version checks.")

        app = agent_os.get_app()
        assert "/company/v1/products" in app.openapi()["paths"]
        db.close()
        print("Company Product example passed without a model.")


if __name__ == "__main__":
    main()
