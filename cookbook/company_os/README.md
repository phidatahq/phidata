# Company Products

Company is opt-in: `AgentOS(db=db, company=CompanyConfig())` enables Product and
Member APIs under `/company/v1`. `CompanyConfig(db=other_db)` overrides the AgentOS
database. Omitting Company adds no Company routes, tables, or background work.
Tables are created lazily through the database adapter on first use.

## Run

From the repository root, after `./scripts/dev_setup.sh`:

```bash
.venv/bin/python cookbook/company_os/products.py
```

The example uses a disposable SQLite file, requires no model or API key, and
creates a Product, adds a member, checks visibility, archives, and restores it.
Use `PostgresDb` for production. `AsyncCompanyService` supports `AsyncSqliteDb`
and `AsyncPostgresDb` with the same methods, awaited.

## Access and versions

Configure AgentOS authentication before using the HTTP API. Company requires a
verified user identity and the existing authorization layer applies `company:read`
or `company:write` scopes. A scope never bypasses Product membership, including
for platform administrators. The service also enforces membership for trusted
application callers; never pass a caller ID taken from an unverified payload.

The creator is the first owner. Owners can edit, archive, restore, and manage
members; members can read. Multiple owners are allowed. Removing or demoting the
named owner selects the oldest remaining owner, with user ID as a tie-breaker.
The last owner cannot be removed or demoted, including by concurrent requests.

Product updates, archive, and restore require `expected_version`. Conflicts return
409; inaccessible records return 404; forbidden actions on visible records return
403. Member PUT and DELETE requests do not require a version. Membership changes
are serialized in storage, and changes to the named owner increment the Product
version. List responses use `{"data": [...]}` and apply membership before pagination.

This example covers Products and Members. Projects, Tasks, files, agents, and
background execution are not part of this foundation.

## Integration tests

Use a disposable PostgreSQL database and set `COMPANY_TEST_POSTGRES_URL`, for example
a local `postgresql+psycopg://` URL. Then run:

```bash
.venv/bin/pytest libs/agno/tests/unit/company libs/agno/tests/integration/company
```

Tests create and remove isolated PostgreSQL schemas and use temporary SQLite files.
Without the environment variable, PostgreSQL integration cases are skipped.
