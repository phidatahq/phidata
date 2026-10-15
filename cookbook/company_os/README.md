# Company OS

Company adds Products to AgentOS. A Product has a name, purpose, owner, ID,
version, and timestamps. No agent, model, or OS Manager is required.

## Run the example

```bash
.venv/bin/python cookbook/company_os/products.py
```

The example uses SQLite at `tmp/company_products.db`. It creates a Product,
reads and updates it, checks a stale edit is rejected, and deletes that Product.
It needs no tokens, API keys, or model calls.

To run the same example with PostgreSQL:

```bash
export COMPANY_DATABASE_URL='postgresql+psycopg://postgres:password@localhost:5432/company_demo'
.venv/bin/python cookbook/company_os/products.py
```

Use SQLite for local development and PostgreSQL for production.

## Enable Company and create its tables

```python
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, CompanyConfig

agent_os = AgentOS(
    db=SqliteDb(db_file="tmp/company.db"),
    company=CompanyConfig(),
)
agent_os.company.initialize_schema()
app = agent_os.get_app()
```

`CompanyConfig(db=company_db)` overrides `AgentOS.db`. The database is resolved
once, including across route resyncs. Synchronous `SqliteDb` and `PostgresDb`
are supported; SQLite requires a file so worker threads share the same storage.
Missing or unsupported databases fail during construction.

The table definitions live in `libs/agno/agno/os/company/storage.py`.
`initialize_schema()` creates two tables:

| Table | Contents |
| --- | --- |
| `company_products` | Product ID, name, purpose, owner ID, version, created/updated timestamps |
| `company_schema_version` | The initial Company schema version, `1` |

PostgreSQL uses the configured `db_schema` (default `ai`); SQLite uses the selected
database file. These tables belong to Company and do not require changes to the
generic Agno database adapters or a separate migration revision for this first schema.

Initialization is explicit: constructing AgentOS, `get_app()`, and startup never
create Company tables. Run `initialize_schema()` before serving requests, or
`await ainitialize_schema()`. Repeating it preserves records. Concurrent initializers
are serialized and failed initialization rolls back. Unknown Company tables or
unsupported versions are rejected without resets or automatic migrations.
Omitting `company` adds no Company routes, imports, storage, or background work.

## Local access and authenticated deployments

The example runs without authentication. Every HTTP caller shares the `local`
owner and can manage its Products. Query parameters and headers cannot choose
another owner. This is a simple local development setup, with no user isolation.

When AgentOS authentication is configured, Company requires a verified human caller
and `company:read`, `company:write`, or `company:delete` permission. Creation assigns
that caller as immutable owner. Only that owner can list, read, edit, or delete the
Product; administrators do not bypass ownership. Foreign and missing IDs both return
404. Service accounts and reserved identities are rejected. Auth-excluded routes
still require authority inside the service.

Managed permissions are checked on every operation and again after acquiring the
mutation lock. PostgreSQL uses row locks; SQLite serializes writers before reading
the Product version. Token-scope deployments retain AgentOS token lifetime and
revocation behavior. Revocation does not undo committed work.

The Python service API requires the existing trusted `authorization_scope` and
`RunAuthorization`; the no-auth convenience is scoped to local HTTP requests.
Every public operation has an async twin that runs synchronous database and policy
work in worker threads.

## HTTP API

| Operation | Request |
| --- | --- |
| Create | `POST /company/v1/products`, body: `name`, `purpose` |
| List | `GET /company/v1/products?limit=50&offset=0` (limit 1–100) |
| Read | `GET /company/v1/products/{id}` |
| Update | `PATCH /company/v1/products/{id}`, body: `expected_version` and `name` and/or `purpose` |
| Delete | `DELETE /company/v1/products/{id}?expected_version=1` |

Bodies reject extra fields; names and purposes must be nonblank. Updates increment
the version. Updates and deletes with stale versions return 409. Deletion is permanent.
Uninitialized storage returns 503 with an initialization instruction.

`GET /config` includes `os_manager_enabled`. It is true when OS Manager is configured
and false for manual Company Products alone. It reports capability, not permission.

## Tests

```bash
.venv/bin/pytest libs/agno/tests/integration/company
```

SQLite tests use temporary files and always run. Set `COMPANY_TEST_DATABASE_URL`
to a disposable PostgreSQL database to run the PostgreSQL cases too; they use unique
schemas and remove those schemas afterward. See `TEST_LOG.md` for recorded results.

Projects, Tasks, Product Manager, tools/MCP, execution, files, and frontend work are
outside this initial example.
