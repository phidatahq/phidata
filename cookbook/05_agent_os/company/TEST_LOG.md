# Company Product validation

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

**Description:** `GET /config` now reports `os_chat_enabled`. Tested OS Manager omitted,
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
