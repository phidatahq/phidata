# Company validation

## Backend review — 14 October 2026

### PostgreSQL integration suite

**Status:** PASS

**Description:** `pytest libs/agno/tests/integration/company` in an isolated dependency
environment against a disposable PostgreSQL database: **37 passed, 1 skipped**.
The skipped test requires the separate AgentOS Manager implementation. Two existing
OpenAPI duplicate-operation warnings remain.

**Result:** Verified persistence, membership and scope enforcement, optimistic
concurrency, idempotency, explicit human review, recurring work, durable dispatch,
cancellation and recovery. Rejected queue claims now release their Company run
reservation without an HTTP history read. MCP transport tests verify authenticated
Company access and reject identity substitution through tool arguments. Models and
coding adapters in this suite are deterministic fixtures, with no provider calls.

### Schema initialization

**Status:** PASS

**Description:** The five unreleased prototype migrations were replaced with one
current initializer. It retains version 5 for existing pilot databases. Fresh and
repeated initialization passed. A populated older prototype is rejected without
changing its data or schema version.

**Result:** No automatic migration at server startup and no destructive reset.

### manual.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/company/manual.py` against a fresh UTF-8
PostgreSQL database after explicit initialization.

**Result:** One Product, Project and Task persisted; explicit human transitions
reached Done and the Project reported one accepted, completed Task. No model calls.

### Format and validation

**Status:** PASS

**Description:** Ran `./scripts/format.sh` and `./scripts/validate.sh` in the development
environment. Both passed, including mypy for 1,129 framework and 21 CLI source files.
Unrelated baseline formatting was restored after the scripts ran.

## Boundaries

This slice has explicit execution and human acceptance. Automatic Ready pickup and
verified PR merge acceptance are a separate slice, as is the built-in Product Manager.
The local tests above do not establish hosted deployment, frontend behavior or coding
workspace isolation. Company uses each configured worker's workspace; operators must
provide an appropriate isolated worker when needed.

## Merged Manager and database defaults — 15 October 2026

**Status:** PASS

**Description:** Refreshed against main with the merged Manager. Company inherits
AgentOS.db unless explicitly overridden. The Company, Manager and run authorization
suites passed: 334 passed, 1 optional compatibility test skipped.

**Result:** Disposable PostgreSQL persistence, database defaults, override precedence,
unsupported database rejection, queue authority restoration and Manager permissions
passed. Format and validation scripts passed. No live provider calls.
