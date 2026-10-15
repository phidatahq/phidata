# Company Products

Company adds manual, authenticated Products to AgentOS without a model or OS Manager.
A Product has a name, purpose, accountable human owner, ID, version, and timestamps.

```python
from agno.db.postgres import PostgresDb
from agno.os import AgentOS, Authorization, CompanyConfig

agent_os = AgentOS(
    db=PostgresDb(db_url=database_url),
    company=CompanyConfig(),
    authorization=Authorization(verification_keys=verification_keys),
)
assert agent_os.company is not None
agent_os.company.initialize_schema()  # explicit deployment step
app = agent_os.get_app()
```

`CompanyConfig(db=company_db)` overrides `AgentOS.db`. The database is resolved once,
including across route resyncs. Only synchronous `PostgresDb` is supported initially;
missing or unsupported databases fail during construction. Company uses the database's
configured schema (`db_schema`, default `ai`), with `company_products` and
`company_schema_version` tables. Use a separate database schema for an independent Company.

Constructing AgentOS, calling `get_app()`, and application startup do not initialize
Company storage. Run `initialize_schema()` explicitly before serving traffic (or
`await ainitialize_schema()`). Repeating initialization preserves records; concurrent
initializers are serialized. The initial schema is version 1. Unrecognized Company
tables or unsupported versions fail without automatic migrations or destructive resets.
Omitting `company` adds no Company routes, imports, storage initialization, or background work.
Other configured AgentOS features retain their own storage behavior.

`GET /config` includes `os_chat_enabled`, a boolean the frontend can use to decide
whether to show OS chat. It is true when OS Manager is configured, and false for
manual Company Products alone: this slice does not include a Product/Company Manager.
This reports configured capability, not caller execution permission; existing
AgentOS authorization still applies. Older server responses that omit the field
parse as false in the Python client.

## Access and concurrency

- Creation assigns the authenticated caller as the immutable human owner. Owner IDs
  cannot be supplied in request bodies. The identity provider must issue human identities
  for this API; first-party service accounts, scheduler identities, anonymous callers,
  and built-in MCP OAuth identities cannot operate on Products.
- Only the owner can list, read, update, or delete their Product. List filtering occurs
  in SQL before pagination. Administrators do not bypass ownership. A missing Product
  and another user's Product both return 404. Sharing and ownership transfer are not included.
- AgentOS authorization must also grant `company:read`, `company:write`, or
  `company:delete`, as appropriate. Configure `authorization=Authorization(...)` (or
  the existing `authorization=True` setup). Company fails closed without caller authority,
  even on an otherwise unauthenticated OS or an authentication-excluded route.
- Every service operation checks the current AgentOS provider. Managed role changes
  take effect on the next check, including retries with the same token. Token-scope-only
  deployments retain AgentOS's token lifetime/revocation semantics; Company does not
  introduce a token revocation system. Mutation permission is checked again after
  acquiring the Product row lock. Revocation does not undo a committed operation.
- Updates and deletes require `expected_version`. A successful update increments the
  version. Concurrent writers using the same version cannot both succeed: a stale write
  returns 409. Read again and deliberately reconcile changes before retrying.
- Removal is permanent: `DELETE` removes only the owned Product at the supplied version.
  There is no archive, restore, audit history, or idempotency key in this slice.

The policy lives in `CompanyService`, shared by the HTTP routes and its Python API.
Python callers use the existing trusted `authorization_scope`/`RunAuthorization` API;
never build authority from model arguments or unverified user input. Each operation has
an async twin (`acreate_product`, `alist_products`, `aget_product`, `aupdate_product`,
`adelete_product`); synchronous PostgreSQL and provider checks run in worker threads.

## HTTP API

| Operation | Request | Required permission |
| --- | --- | --- |
| Create | `POST /company/v1/products`, body: `name`, `purpose` | `company:write` |
| List owned Products | `GET /company/v1/products?limit=50&offset=0` (limit 1–100) | `company:read` |
| Read | `GET /company/v1/products/{id}` | `company:read` |
| Update | `PATCH /company/v1/products/{id}`, body: `expected_version` and `name` and/or `purpose` | `company:write` |
| Remove | `DELETE /company/v1/products/{id}?expected_version=1` | `company:delete` |

Bodies reject extra fields; names and purposes must be nonblank. Uninitialized storage
returns 503 with an explicit initialization instruction. Initialization is not an HTTP endpoint.

## Run the model-free example

Use a disposable PostgreSQL database and the repository development environment:

```bash
export COMPANY_DATABASE_URL='postgresql+psycopg://postgres:password@localhost:5432/company_demo'
.venv/bin/python cookbook/05_agent_os/company/products.py
```

The script uses a generated local JWT signing secret and FastAPI's local test client.
It creates only its own Product, verifies read/list/update, checks a stale edit is rejected,
and deletes that Product. It uses `company_products_demo` as its database schema.
Expected output: `PASS: authenticated Product CRUD, scoped listing, and version conflicts without a model`.
The expected 409 and final 404 are also logged. No external model calls occur.

For the PostgreSQL tests, set `COMPANY_TEST_DATABASE_URL` to a disposable database and run
`pytest libs/agno/tests/integration/company`. Tests create unique schemas and remove those
schemas afterward. They skip if that variable is absent.

This example does not include Tasks, Projects, agents, model selection, Product Manager,
MCP/tools, files, execution, queues, scheduling, sandboxes, GitHub, or a frontend.
