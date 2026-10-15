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

## Foundation scope cleanup — 15 October 2026

### Company, Manager, authorization and scheduler regression suite

**Status:** PASS

**Description:** 577 tests passed with no skips against disposable PostgreSQL. The
Manager delegation test now exercises the merged `OSManager` instead of skipping
an obsolete module. Added coverage rejecting all current reserved Manager IDs as
Company workers. Existing duplicate OpenAPI operation-ID warnings remain.

**Result:** Company behavior passes with all database/model adapter changes removed.
The PR changes only Company files and its AgentOS integration points.

### manual.py and with_agents.py

**Status:** PASS

**Description:** Applied the migration and ran `manual.py` twice against a separate
disposable database; both runs retained one completed Task. Constructed
`with_agents.py` with OS Manager and an optional Codex workspace; verified Manager
membership and Company routes without provider calls. Updated the example to
`OSManager(root=...)` and removed obsolete Platform Engineer references.

**Result:** Both examples passed. Initial smoke assertions incorrectly assumed the
registered agent list excluded platform members and every FastAPI router had a
`path`; corrected the checks to use the registered members and OpenAPI paths.

### Format, validation and scope

**Status:** PASS (CI dependency environment)

**Description:** Required format and validation scripts passed in a fresh Python
3.10 environment using the declared `agno[dev]` and workspace `agnoctl` dependencies,
matching CI's dependency setup. Restored only unrelated formatter changes afterward.
Verified the 11 extracted files match the PR base byte-for-byte.

**Result:** The broader Python 3.12 development environment reports 33 mypy errors
in unchanged files; the exact same errors reproduce on the unmodified base.
These are recorded baseline/dependency issues, not fixes included in Company.
