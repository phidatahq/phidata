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

The base checks above cover explicit execution and human acceptance. The follow-up
checks below cover Ready/review automation and the built-in Product Manager.
The local tests above do not establish hosted deployment, frontend behavior or coding
workspace isolation. Company uses each configured worker's workspace; operators must
provide an appropriate isolated worker when needed.

## Ready/review review — 14 October 2026

**Status:** PASS

**Description:** Company PostgreSQL integration plus the complete scheduler unit suite:
**259 passed, 2 Manager-only skips**, two existing OpenAPI warnings. Full format and
validation scripts passed, including framework and CLI mypy.

**Result:** Ready acceptance is picked up once through the durable queue; completion
stops In review. Human acceptance or a read-only check of a human-linked exact GitHub
PR revision can finish review. Tests cover revocation, changed revisions, closed PRs,
bot mergers, stale merges, malformed responses, credential redirects and concurrent
review changes. Slow review checks do not block ordinary schedules, ticks do not
overlap within a poller, and shutdown cancels the check. A full evidence list no longer
blocks verified completion; the merge proof remains in the audit event. Version-5
upgrade preserves work without enrolling legacy Ready Tasks. GitHub responses are
fixtures here; account type is not proof of physical human interaction.

## Built-in Product Manager review — 14 October 2026

**Status:** PASS

**Description:** Full Company integration with scheduler and queue regression tests:
**388 passed, 2 Manager-only skips**. The four built-in tests also passed in the
isolated dependency environment. Full format and validation scripts passed.

**Result:** One framework Agent is reused across Products and resync, manual Company
creates no agent, duplicate IDs fail clearly, and HTTP plus durable task execution
retain the initiating user's Product access. Tests exercise real PostgreSQL and
AgentOS transport with a deterministic model; no paid provider calls.

### with_agents.py

**Status:** PASS

**Description:** Constructed the cookbook app with and without the separate Manager
implementation. The combined configuration includes Platform Manager, Platform
Builder, Platform Engineer and Product Manager. Repeated resync retains one Product
Manager. Construction checks made no model calls.

### Manager compatibility

**Status:** PASS

**Description:** Composed the full Company stack with Manager PR #11036 at
`01a202354a7e5f5bd7fd0b61f60dc0a7bb7b24d3` in a disposable checkout. Company integration
and Manager unit tests: **209 passed**, with no skipped Company composition tests.

**Result:** Verified Manager delegation with caller identity, automatic Ready pickup,
human review boundaries and repeated resync. Composition required retaining both
additive exports/constructor fields in `os/__init__.py` and `os/app.py`. Neither the
Manager PR nor the concurrent primary checkout was changed. Future Manager changes
need another compatibility run.
## Merged Manager and database defaults — 15 October 2026

**Status:** PASS

**Description:** Refreshed against main with the merged Manager. Company inherits
AgentOS.db unless explicitly overridden. The Company, Manager and run authorization
suites passed: 334 passed, 1 optional compatibility test skipped.

**Result:** Disposable PostgreSQL persistence, database defaults, override precedence,
unsupported database rejection, queue authority restoration and Manager permissions
passed. Format and validation scripts passed. No live provider calls.
