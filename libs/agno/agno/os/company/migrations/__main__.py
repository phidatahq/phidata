"""Run with COMPANY_DATABASE_URL set; secrets are never command arguments."""

import os

from agno.db.postgres import PostgresDb
from agno.os.company.migrations import VERSION, migrate

if __name__ == "__main__":
    migrate(PostgresDb(db_url=os.environ["COMPANY_DATABASE_URL"]))
    print(f"Company schema is current (version {VERSION}).")
