# Company Products

Company is opt-in: `AgentOS(db=db, company=CompanyConfig())` enables Product and
Member APIs under `/company/v1`. `CompanyConfig(db=other_db)` overrides the AgentOS
database. Omitting Company adds no Company routes, tables, or background work.
Tables are created lazily through the database adapter on first use.

## Run

From the repository root, after `./scripts/dev_setup.sh`:

```bash
PYTHONPATH=libs/agno .venv/bin/python cookbook/company_os/products.py
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
PYTHONPATH=libs/agno .venv/bin/pytest libs/agno/tests/unit/company libs/agno/tests/integration/company
```

Tests create and remove isolated PostgreSQL schemas and use temporary SQLite files.
Without the environment variable, PostgreSQL integration cases are skipped.


## Test the HTTP API locally

This foundation exposes backend APIs; it does not include the Company frontend.
The server below persists SQLite data in `tmp/company-os.db`, so Products survive
restarts. It requires no model or provider API key.

In the first terminal, from the PR checkout:

```bash
export PYTHONPATH=libs/agno
export COMPANY_DEMO_SECRET=company-local-demo-signing-key-for-testing-only
.venv/bin/python cookbook/company_os/api.py
```

In a second terminal in the same checkout, use the same local test key:

```bash
export PYTHONPATH=libs/agno
export COMPANY_DEMO_SECRET=company-local-demo-signing-key-for-testing-only
export COMPANY_ALICE_TOKEN="$(.venv/bin/python cookbook/company_os/api.py --token-for alice)"
export COMPANY_BOB_TOKEN="$(.venv/bin/python cookbook/company_os/api.py --token-for bob)"

curl -sS http://127.0.0.1:7777/company/v1/products \
  -H "Authorization: Bearer $COMPANY_ALICE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Documentation","purpose":"Keep documentation accurate"}'
```

Copy the returned `id` into `COMPANY_PRODUCT_ID`, then check isolation and membership:

```bash
export COMPANY_PRODUCT_ID=replace-with-returned-id
curl -i "http://127.0.0.1:7777/company/v1/products/$COMPANY_PRODUCT_ID" \
  -H "Authorization: Bearer $COMPANY_BOB_TOKEN"

curl -sS -X PUT "http://127.0.0.1:7777/company/v1/products/$COMPANY_PRODUCT_ID/members/bob" \
  -H "Authorization: Bearer $COMPANY_ALICE_TOKEN" \
  -H 'Content-Type: application/json' -d '{"role":"member"}'

curl -i "http://127.0.0.1:7777/company/v1/products/$COMPANY_PRODUCT_ID" \
  -H "Authorization: Bearer $COMPANY_BOB_TOKEN"
```

Bob's first read returns 404. After Alice adds him, it returns 200. Both tokens
carry Company read/write scopes; Bob's Product role still prevents owner actions.

```bash
curl -i "http://127.0.0.1:7777/company/v1/products/$COMPANY_PRODUCT_ID/archive" \
  -H "Authorization: Bearer $COMPANY_BOB_TOKEN" \
  -H 'Content-Type: application/json' -d '{"expected_version":1}'

curl -i "http://127.0.0.1:7777/company/v1/products/$COMPANY_PRODUCT_ID/archive" \
  -H "Authorization: Bearer $COMPANY_ALICE_TOKEN" \
  -H 'Content-Type: application/json' -d '{"expected_version":1}'

curl -i "http://127.0.0.1:7777/company/v1/products/$COMPANY_PRODUCT_ID/restore" \
  -H "Authorization: Bearer $COMPANY_ALICE_TOKEN" \
  -H 'Content-Type: application/json' -d '{"expected_version":1}'
```

Expect 403 for Bob, 200 with `version: 2` for Alice's archive, and 409 for the
stale restore. Repeat the restore with `expected_version: 2` to get an active
Product at version 3. Stop the server with Ctrl-C. These tokens expire after an
hour; rerun the token commands when needed. The example key is for local testing.
