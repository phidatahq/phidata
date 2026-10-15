# Company OS validation

## SQLite and PostgreSQL follow-up — October 15, 2026

Source: `ab/company-products`, changes following `095c78f53cf5275291b24106f09043312d4c12a0`.
Python 3.12.8, SQLite 3.47.1, disposable PostgreSQL 16.15, SQLAlchemy 2.1.4,
psycopg 3.3.6, FastAPI 0.143.2, Pydantic 2.14.1. Reused the development venv;
no clean dependency installation, paid/live model calls, or hosted deployment.

### cookbook/company_os/products.py

**Status:** PASS on SQLite and PostgreSQL.

**Description:** Ran the example without authorization, tokens, or model configuration.
SQLite uses `tmp/company_products.db`; PostgreSQL used a disposable database via
`COMPANY_DATABASE_URL`. Both runs explicitly initialized the Company tables, created
one Product with the shared `local` owner, read/listed/updated it, rejected a stale
edit, then deleted only the Product created by that run.

**Result:** `PASS: Product CRUD and version conflicts without a model or auth setup`.
The expected stale-write 409 and post-deletion 404 were observed.

---

### Database parity and framework regression tests

**Status:** PASS.

**Description:** Ran the Company suite together with existing scopes/provider parity,
run authorization, MCP routing, JWT overrides, authorization offloading, authorization
integration/planes/denial messages, Manager, client, and config queue capability tests.
Company cases cover both databases, persistence, concurrent initialization/writers,
initialization rollback, ownership, revocation after lock waits, sync/async parity,
local HTTP CRUD, auth-excluded routes, manually installed auth, and explicit rejection
of in-memory SQLite (worker threads require shared file storage).

**Result:** 714 passed, including 67 Company cases. Warnings cover existing duplicate
OpenAPI operation IDs and short JWT test keys, plus SQLAlchemy's pool deprecation
for the intentionally rejected in-memory URI case. An initial run using `localhost`
stalled and was interrupted; the isolated test and complete rerun using the container's
explicit `127.0.0.1` binding passed. PostgreSQL used unique schemas; SQLite used temporary files.

---

### Repository publication scripts

**Status:** Format PASS; validation FAIL with the approved baseline exception.

**Description:** Ran both `scripts/format.sh` and `scripts/validate.sh`.
Removed only formatter churn in four unrelated, previously clean files.

**Result:** Validation has exactly the same 33 mypy errors in 10 unchanged files as
unchanged main under the same development environment. No new diagnostics. Ruff,
agnoctl mypy, and cookbook pattern checks pass. The maintainer's approved exception
permits publication for review; validation is not green and no merge/deployment is authorized.

---

## Previous PostgreSQL-only validation

Run on October 15, 2026. Python 3.12.8, PostgreSQL 16.15 in a disposable Docker
container, SQLAlchemy 2.1.4, psycopg 3.3.6, FastAPI 0.143.2, Pydantic 2.14.1.
The repository development environment was reused; this was not a clean dependency install.
No paid/live model calls or hosted deployment were used.

### products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/company/products.py` with a disposable
PostgreSQL URL. Verified authenticated create/read/list/update/delete, owner assignment,
and rejection of a stale update. The script removed only the Product it created.

**Result:** `PASS: authenticated Product CRUD, scoped listing, and version conflicts without a model`.
Expected 409 and final 404 responses are logged.

---

### Product acceptance tests

**Status:** PASS

**Description:** `libs/agno/tests/integration/company/test_products.py` covers
configuration inheritance/override/errors, disabled behavior, no assembly DDL,
repeatable/concurrent initialization, preservation of unknown existing tables,
persistence, scoped pagination, ownership, forged/anonymous/service identity rejection,
live role revocation, stale/concurrent writes, resync, and sync/async parity/offloading.

**Result:** 36 tests passed against disposable PostgreSQL. A managed-role HTTP test
first reproduced a stale request-cache decision during a Product row-lock wait;
Company now invalidates those cached reads before rechecking, and the test passes.
The OpenAPI inspection reports an existing duplicate operation ID in the components router.

---

### Routing and authorization regressions

**Status:** PASS

**Description:** Ran the 36 Company tests together with existing scopes, provider parity,
run authorization, MCP routing, JWT overrides, authorization offloading, JWT authorization,
Authorization object, authorization planes, and denial-message tests.

**Result:** 442 passed. Existing warnings concern a duplicate components OpenAPI operation
ID and short JWT keys in existing authorization test fixtures. No live model calls.

---

### Repository publication scripts

**Status:** FAIL

**Description:** Ran `scripts/format.sh` and `scripts/validate.sh` using Ruff 0.15.20
and mypy 2.1.0. Ran validation on unchanged base
`d21622a3d378ed75f3fadbe7cc853c5ecba1bb41` with the same environment before implementation.

**Result:** Format passed. Four unrelated formatting changes were removed from the diff.
Validation reports the same 33 mypy errors in 10 unchanged framework files on both base
and the implementation, with no additional diagnostics. Ruff, agnoctl mypy, and the
cookbook pattern check pass. No unrelated fixes or weakened checks are included.
The required publication gate is not satisfied; passing Company tests do not waive it.

---

### OS chat capability follow-up

**Status:** PASS (focused tests); repository validation retains the baseline failure above.

**Description:** `GET /config` now reports `os_manager_enabled`. Tested OS Manager omitted,
explicitly disabled, enabled through the registry, and explicitly configured, both with
and without Company. Verified route resync, no Company database connection during config
discovery, and older-server client compatibility. No Product Manager is implemented.

**Result:** 207 tests passed across `test_manager.py`, `test_client.py`, and
`test_config_queue_capabilities.py`. The earlier 442-test Product/regression run was on
head `9e6ec23b489e9ffb294acf12d0ce0007ec24548a`; it was not rerun for this config-only follow-up.
Both publication scripts ran again: format passed and validation returned the same 33
baseline mypy errors with no added diagnostics. The approved baseline exception applies.
No Manager implementation or Product service/storage behavior changed.

---

Naming correction: the field is `os_manager_enabled`. After preserving the concurrent
merge of main, all eight configuration/resync cases and the older-server client test
passed (9 total). Format passed; validation retained the same 33 baseline diagnostics.
