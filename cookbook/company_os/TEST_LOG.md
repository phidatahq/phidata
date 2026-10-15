# Company foundation test log

Tested October 15, 2026, using the development environment and disposable databases.
No model or provider calls were made.

### products.py

**Status:** PASS

**Description:** `PYTHONPATH=libs/agno .venv/bin/python cookbook/company_os/products.py`
creates a Product and its first owner, adds a member, verifies visibility for the
owner/member/outsider, archives, restores, and checks the mounted API on SQLite.

**Result:** `Company Product example passed without a model.` An existing
Components OpenAPI duplicate operation-ID warning was emitted for `get_config`.

---

### Company unit and integration tests

**Status:** PASS

**Description:** `pytest libs/agno/tests/unit/company libs/agno/tests/integration/company`
with `PYTHONPATH=libs/agno` and `COMPANY_TEST_POSTGRES_URL` pointing at disposable
PostgreSQL 16. SQLite uses temporary files. Both sync and async adapters run the
same storage, authorization, version, concurrency, persistence, migration,
default/override database, and HTTP contracts. The cookbook and APIs need no model.

**Result:** 46 passed, no skips. Concurrent owner removals preserve one owner;
conflicting Product writes have one winner; failed creation rolls back the Product;
revoked actors are rejected inside the mutation transaction. General provisioning
and migration checks leave Company tables absent until Company storage is used.

---

### Related regression tests

**Status:** PASS

**Description:** Database round-trip serialization, table resolution cache,
PostgreSQL unit tests, migration utilities, schema-version signature parity, and
AgentOS information/MCP routing tests, alongside the then-current Company tests.

**Result:** 170 passed, 28 skipped (38 Company and 132 existing regression tests).
The eight additional override/provisioning cases are included in the final
46-test Company result above. The existing regression skips were not claimed as
PostgreSQL Company coverage; every Company PostgreSQL case ran.

---

### Repository publication checks

**Status:** FAIL

**Description:** Ran `./scripts/format.sh` and `./scripts/validate.sh`. Removed
formatter-only changes to four unrelated files from this PR.

**Result:** Formatting, ruff checks, agnoctl mypy, and cookbook pattern checks pass.
Agno mypy reports 33 errors in 10 files. Running validation on unchanged main at
`0d3200f1664105a87455cd9918037e4c4d56231c` reports the same 33 errors; comparison
by file and diagnostic (ignoring shifted line numbers) shows no added or removed
errors. The full validation gate is not green. The PR remains draft.

---


## Review follow-up — October 15, 2026

### Database configuration regressions

**Status:** PASS

**Description:** Added full and partial registry-reload cases for SQLite and
PostgreSQL, explicit Company table overrides, unrelated session-table overrides,
and async PostgreSQL round trips with nondefault jobs table and schema policy.

**Result:** Before fixing, the existing table-name whitelist test and six new
cases failed. Partial configuration probes then exposed two additional failing
reload cases. All now pass: unspecified registered table names survive cloning,
Company overrides are applied, and `job_table` / `create_schema` survive async
PostgreSQL serialization. The unsupported-adapter fallback remains covered.

---

### Combined Company and related regression selection

**Status:** PASS

**Description:** Company unit/integration tests plus database config resolution,
serialization, table resolution, PostgreSQL unit tests, migration utilities,
schema-version signatures, and AgentOS information/MCP routing tests.

**Result:** 201 passed, 28 existing regression skips. All 46 Company tests ran,
including disposable PostgreSQL 16 and SQLite, sync and async. The model-free
`products.py` cookbook also passed again.

---

### api.py

**Status:** PASS

**Description:** Started the persistent SQLite API on localhost and used the CLI
to mint Alice/Bob test tokens. Exercised the README workflow over real HTTP.

**Result:** Anonymous request 401; Product creation 200; Bob's initial read 404;
adding Bob 200; Bob's read 200; Bob's archive 403; Alice's archive 200/version 2;
stale restore 409; current restore 200/version 3; member removal 204; revoked
Bob's read 404. Server shut down cleanly. No model or provider calls were made.

---
