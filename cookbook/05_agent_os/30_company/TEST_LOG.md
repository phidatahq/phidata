# Test Log: Company Products

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py`
with the development environment on October 15, 2026, after simplifying the
internal scope-map handoff (SQLAlchemy 2.0.54). SQLite persistence,
two users, unscoped and owner-filtered listings, soft delete, include_deleted,
and restore were exercised.

**Result:** All assertions passed. Output:

```text
Isolation off: 2 Products
Isolation on for alice: 1 Product
Soft delete, include_deleted and restore passed
```

---


### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py`
on October 15, 2026 using SQLite and the development environment. Tested two
owners, unscoped and scoped listing, reasoned Project transitions, status
filtering, soft delete and restore without a model.

**Result:** All assertions passed; output: `Company projects lifecycle passed`.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py`
on October 15, 2026 using SQLite and the development environment. Tested
Backlog creation, executor and acceptor recording, frozen scope, returning to
Backlog and clearing acceptance, review/completion, filtering, delete and
restore. This example manages records without executing a model.

**Result:** All assertions passed. Output:

```text
Accepted scope is protected
Company tasks lifecycle passed
```

---

The existing `01_manage_products.py` was also rerun successfully with its
original output and assertions unchanged.


### Rebase verification: all Company examples

**Status:** PASS

**Description:** Reran `01_manage_products.py`, `02_manage_projects.py`, and
`03_manage_tasks.py` on October 15, 2026 after rebasing onto Products commit
`850ebb87a6a78c73392fd3c0a998ce9c18f8a823`, including its database shutdown
and async configuration reconstruction fixes. The new Project/Task inserts
also use the same required-row return convention as Products.

**Result:** All assertions passed. Products reported two unscoped records,
one Alice-owned record, and successful archive/restore checks. Projects
reported lifecycle success. Tasks reported protected accepted scope and
lifecycle success.

---


### Company-wide work reads

**Status:** PASS

**Description:** Reran all three cookbook files after rebasing onto Products
commit `c9ec5af77fb229a291dea1148eeb445331d1013d` and adopting its shared-read
behavior for Projects and Tasks. The direct manager examples retain explicit
owner filters.

**Result:** All cookbook assertions passed. The Company router and integration
run also passed 260 tests, including company-wide reads, paginated status
filters, shared Product/Project assignment, and owner-scoped writes and
transitions across sync/async SQLite and PostgreSQL.

---

### 02_manage_projects.py — collaborative HTTP edits and transitions follow-up

**Status:** PASS

**Description:** Reran the Project cookbook after allowing resource-authorized callers to edit and transition another creator's Project through HTTP.

**Result:** `Company projects lifecycle passed`. The cookbook checks direct-manager lifecycle, owner filtering, deletion, and restoration; separate HTTP regressions verify collaboration.

---

### 03_manage_tasks.py — collaborative HTTP edits and transitions follow-up

**Status:** PASS

**Description:** Reran the Task cookbook after allowing resource-authorized callers to edit Backlog Tasks and perform lifecycle transitions through HTTP.

**Result:** `Accepted scope is protected` and `Company tasks lifecycle passed`. Separate HTTP regressions verify cross-user acceptance, cancellation, returning to Backlog, attribution, and executor authorization.

---

## Playbook and Product Manager delivery

### 01_manage_products.py, 02_manage_projects.py, 03_manage_tasks.py

**Status:** PASS

**Description:** Reran all three existing files in `cookbook/05_agent_os/30_company/`
with the development environment on October 15, 2026. Products, Projects and
Tasks retain their owner filters, transitions, soft deletion and restoration.

**Result:** Each file completed successfully; accepted Task scope remained protected.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` on
SQLite, sync and async. Created Product and company wiki namespaces, updated
status with its version, rejected a stale edit and saved learning decisions.

**Result:** Both paths completed without a model or provider credentials.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py`.
Configured a standalone Product Manager using the registry model, configured
explicit MCP toolkit publication, and called the bounded tools with trusted
application run context.

**Result:** Backlog proposal, status and decision persisted with the caller's
identity. No model call was made; live provider behavior was not tested.

---


### Final merged-base verification — October 16, 2026

**Status:** PASS

**Description:** Reran every file in `cookbook/05_agent_os/30_company/`:
`01_manage_products.py`, `02_manage_projects.py`, `03_manage_tasks.py`,
`04_manage_playbook.py`, and `05_product_manager.py`. All completed successfully
on the final implementation. The tested PR 2 head and merged main commit
`a88f7a518c61c2d8a76b4407ed7c1d07378b77fe` have identical Git trees; PR 3
was rebased onto that merge before publication.

**Result:** Products and Projects passed lifecycle checks; Tasks protected
accepted scope. Sync/async wiki edits rejected stale versions and persisted
learning decisions. Product Manager's bounded tools saved a caller-owned
Backlog proposal, status and decision. No provider calls were made.

The full database and AgentOS unit suites passed **6,079 tests**, with **15
conditional skips**. Company SQLite/PostgreSQL integrations (sync and async)
and filesystem integrations passed **238 tests**, with no skips. Shared
filesystem/context unit tests plus the new four-adapter parity tests passed
**840 tests** (overlapping the integration count). Format and validation passed,
including both mypy checks; the validate output was read.

---


### Review fixes — October 16, 2026

**Status:** PASS

**Description:** Reran all five files in `cookbook/05_agent_os/30_company/`:
`01_manage_products.py`, `02_manage_projects.py`, `03_manage_tasks.py`,
`04_manage_playbook.py`, and `05_product_manager.py`, after fixing Company
decision recall, tool instructions, author attribution and wiki routing.

**Result:** All cookbook assertions passed. The shared Company decision context
includes human entries; direct CompanyTools/MCP calls no longer claim Product
Manager authorship. Actual offline sync/async Product Manager runs verified
human decision context and the exposed tool names in system prompts.
The broader regression run passed **1,516 tests**, with no skips, covering
Company routes/tools, scopes, manager composition, diagnostics, learning,
context providers, and Company SQLite/PostgreSQL storage in both execution
modes. All provider calls remained offline. The original full database/OS
unit-suite results above precede this follow-up; those full suites were not
rerun for these focused fixes. Format and validation passed.

---


### Async filesystem transaction review — October 16, 2026

**Status:** PASS

**Description:** Reran `01_manage_products.py`, `02_manage_projects.py`,
`03_manage_tasks.py`, `04_manage_playbook.py`, and `05_product_manager.py`
after fixing async SQLite outer transaction ownership.

**Result:** All five cookbooks passed. Product/Project/Task lifecycle checks,
sync/async wiki version conflicts, and bounded Product Manager proposal, status
and decision writes passed. No provider calls were made.

The focused filesystem review reproduced four failing cases: exception and
cancellation after savepoint release persisted an async SQLite write on both
file-backed and in-memory databases. Explicit outer BEGIN fixes all four while
respecting caller-managed transaction hooks. The 33 new regression cases cover
legacy migrations (missing/nullable user column), data and partition retention,
partial DDL rollback, migration cancellation, partial-move rollback, cold-create
cancellation and retry, and durable connection recovery after cancellation.
All 33 passed on Python 3.10 and Python 3.12 with SQLite and PostgreSQL.

Filesystem/context units and filesystem/Company integrations passed **1,082
tests**, with no skips (includes the 33 cases above). Format and validation
passed; all validation output, including both mypy summaries, was read.
In-memory SQLite remains connection-owned: driver cancellation that invalidates
its only connection discards the database; durable cancellation recovery is
verified on file-backed SQLite and PostgreSQL.

---

Final full-suite rerun after this fix: **6,085 passed, 15 skipped** across
`libs/agno/tests/unit/db` and `libs/agno/tests/unit/os`. The temporary MongoDB
container was removed after the run; existing PostgreSQL services were retained.

### 01_manage_products.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/01_manage_products.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/02_manage_projects.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/05_product_manager.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.


### Execution and attention — October 16, 2026

**Status:** PASS

**Description:** Reran `01_manage_products.py`, `02_manage_projects.py`,
`03_manage_tasks.py`, `04_manage_playbook.py` and `05_product_manager.py` from
`cookbook/05_agent_os/30_company/` using the development environment after
merging Playbook fixes at `769eee4306558569988b346a8bd71dc9b945b700`.
The Task cookbook now supplies its executor registry at acceptance.

**Result:** Every existing assertion passed. Products/Projects/Tasks retain their
lifecycle behavior; wiki edits reject stale versions; Product Manager tools
persist proposals, status and decisions. No model calls were made.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` twice:
default SQLite Company/session storage with a PostgreSQL durable queue, and
`COMPANY_DB=postgres` for PostgreSQL Company/session/queue storage. The real
application lifespan starts the queue worker. A registered workflow receives
only brief/wiki/evidence, executes an accepted Task, and persists its result.

**Result:** Both runs reached In review, returned the original run for the
repeated attempt, and listed one ordinary run in the Task session. Attention
returned `{"proposals": 0, "in_review": 1, "failed": 0}`. Both workers shut down
cleanly and the example removed its temporary schema. SQLite emitted the
existing warning that its session fallback does not provide PostgreSQL's
attempt fencing. No provider calls were made.

---

### Execution regression checks — October 16, 2026

**Status:** PASS

**Description:** Ran the complete `libs/agno/tests/unit/db` and
`libs/agno/tests/unit/os` suites, all Company database integrations, and the
final execution authorization/error-handling tests. Tests use temporary SQLite
files and isolated PostgreSQL schemas with offline model fixtures.

**Result:** Full unit suites: **6,095 passed, 15 skipped**. Company integrations:
**175 passed**, no skips, across sync/async SQLite and PostgreSQL. Final execution
route tests: **13 passed** (10 overlap the full suite). These include the final
503 response when Company storage is absent and 404 for deleted Product context
without reserving a run. Format and validation passed, including both mypy
checks, and all validation output was read. Validation used the clean Python
3.10 environment; tests and cookbooks used the Python 3.12 development environment.

---

### Execution review fixes — October 16, 2026

**Status:** PASS

**Description:** Reproduced rejected input consuming a Task attempt and
`failed=false` omitting pending Tasks whose result is JSON null. All 16 new
regression cases failed before the fix across sync/async SQLite and PostgreSQL;
input rejection was checked for agents, teams and workflows. The existing run
validator now checks input before reservation, and nonfailed filters include
null extracted result statuses.

**Result:** Execution, Task router/isolation and Task storage regressions passed
**197 tests**, including all 16 new cases. Rejected input leaves Ready and its
transition history intact; correcting the executor schema allows attempt 1 to
complete. Pending and unstarted Tasks both appear in nonfailed counts before
pagination; failed Tasks appear only in the failed filter. Reran
`cookbook/05_agent_os/30_company/06_execute_tasks.py` with SQLite and with
`COMPANY_DB=postgres`: both passed through the real durable worker, returning
the first run on duplicate start and reporting one Task In review. No provider
calls were made. Format and validation passed and their output was read.
The full unit-suite result above predates these focused review fixes.

---

### Attention lifecycle and reserved executors — October 16, 2026

**Status:** PASS

**Description:** Added 56 cases: failure attention after cancellation, Backlog,
reacceptance, review and completion; all four framework-reserved executor IDs
at acceptance/start on all four SQL adapters; and reserved-ID exclusion during
registry mounting. The initial run reproduced 38 failures, with 18 existing
reserved-specialist protections already passing. Failed/nonfailed predicates
now partition Tasks by active error state while retaining SQL/JSON null handling.

**Result:** **253 targeted tests passed**, including all 56 new cases and the
previous review regressions. Per-Product and company-wide attention clear handled
failures, pagination totals remain correct, and error results remain intact as
history. Product Manager and OS Manager are rejected explicitly even with a
custom registry resolver. Reran `06_execute_tasks.py` with SQLite and
`COMPANY_DB=postgres`; both completed with one Task In review. Format and
validation passed, including both mypy checks, and their output was read. No
provider calls were made. The earlier full unit-suite result remains the baseline.

---

### Rebase onto merged Playbook — October 16, 2026

**Status:** PASS

**Description:** Rebased PR 4 onto `main` at
`f801d7c7421e7a7da5d6cee42fd4b0b8bceabe98`, including the final Playbook async
filesystem transaction fixes. Preserved both branches' test-log entries during
the sole conflict. Commit and tree comparisons confirmed the execution changes
were preserved and the inherited filesystem code matches main.

**Result:** **286 targeted tests passed**: Company execution/Task regressions
plus the 33 filesystem transaction cases from the merged base. All six Company
cookbooks passed, and execution also passed with PostgreSQL session storage.
Format and validation passed; both mypy checks and all script output were read.
No provider calls were made. The full unit-suite figures above remain their
historical baseline; this rebase used focused regression coverage.

---

### Initial Task schema — October 16, 2026

**Status:** PASS

**Description:** Removed the Company execution migration and its version
registration because Company tables have not been released. Execution references,
evidence and results remain part of the initial Task schema. Replaced the upgrade
test with fresh custom-table creation and execution checks on sync/async SQLite
and PostgreSQL. Restored the unrelated migration unit tests to their main versions.

**Result:** **186 targeted tests passed**, covering execution, authorization,
fresh Task schema/index creation and the restored migration suites. Both
execution cookbook modes passed. Format and validation passed (mypy: 1,146 core
files and 21 CLI files), and all output was read. No provider calls were made.
Earlier migration test entries describe the implementation before this simplification.

---

## Queue rejection and simplification follow-up — October 16, 2026

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` with the development environment.

**Result:** Product CRUD, owner filters, deletion and restore.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` with the development environment.

**Result:** Project lifecycle and Product containment.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` with the development environment.

**Result:** Registry-backed acceptance and explicit Task transitions.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` with the development environment.

**Result:** Sync/async wiki and decision-log operations.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` with the development environment.

**Result:** Product Manager construction and tool publication without provider calls.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` with the development environment.

**Result:** Both default SQLite sessions and COMPANY_DB=postgres passed with a real PostgreSQL durable queue: accepted execution, duplicate run identity, stored results, history and attention. No provider calls.

---

### Queue rejection regression checks

**Status:** PASS

**Description:** Full database/OS unit suites and all Company integrations plus execution authorization tests.

**Result:** 6,104 unit tests passed, 15 skipped; 306 integration/authorization tests passed. Added 46 regression cases covering all three executor types, all four Company adapters, unchanged Task state/results/attempts after rejection, concurrent duplicates, and recovery after enqueue with revocation and cancellation. PostgreSQL queue JSON round-trips recover correctly into SQLite Task storage. Both format and validate scripts passed; validation output was read, including mypy success for 1,146 core and 21 CLI files.

## Release-test cancellation and adapter follow-up — October 16, 2026

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` with the development environment.

**Result:** Product CRUD, ownership, soft deletion and restore passed.

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` with the development environment.

**Result:** Project lifecycle and Product containment passed.

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` with the development environment.

**Result:** Registry-backed acceptance and explicit Task lifecycle passed.

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` with the development environment.

**Result:** Sync/async wiki and decision-log operations passed.

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` with the development environment.

**Result:** Product Manager construction and bounded tool publication passed without provider calls.

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` with the development environment.

**Result:** Default SQLite sessions and COMPANY_DB=postgres both passed with a real PostgreSQL durable queue. Execution, duplicate starts, paged history and attention passed without provider calls.

### Release-test regression checks

**Status:** PASS

**Description:** Cancellation visibility/retry, attention lifecycle, unsupported database responses, and the full database/OS unit suites.

**Result:** 247 execution/route tests passed on sync/async SQLite and PostgreSQL; 6,104 full unit tests passed, 15 skipped. Format passed. Validation passed on this branch and unchanged main at `7f5dcdf53d` with the same clean Python 3.10 environment and separate mypy caches: zero errors on either. Output was read, including mypy success for 1,146 PR core files, 1,144 main core files and 21 CLI files on each. The release reports' unannotated `prior` variables belong to later automatic-acceptance code and are absent from PR 4.


## Main integration and round-3 execution review — October 16, 2026

### 01_manage_products.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/01_manage_products.py` after incorporating the merged release fixes and the final-attempt attention and revoked-submission repairs.

**Result:** Completed all assertions using the rebased code, including the merged Company routing and nullable tool-argument fixes. No live model calls were made.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/02_manage_projects.py` after incorporating the merged release fixes and the final-attempt attention and revoked-submission repairs.

**Result:** Completed all assertions using the rebased code, including the merged Company routing and nullable tool-argument fixes. No live model calls were made.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` after incorporating the merged release fixes and the final-attempt attention and revoked-submission repairs.

**Result:** Completed all assertions using the rebased code, including the merged Company routing and nullable tool-argument fixes. No live model calls were made.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` after incorporating the merged release fixes and the final-attempt attention and revoked-submission repairs.

**Result:** Completed all assertions using the rebased code, including the merged Company routing and nullable tool-argument fixes. No live model calls were made.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/05_product_manager.py` after incorporating the merged release fixes and the final-attempt attention and revoked-submission repairs.

**Result:** Completed all assertions using the rebased code, including the merged Company routing and nullable tool-argument fixes. No live model calls were made.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` after incorporating the merged release fixes and the final-attempt attention and revoked-submission repairs.

**Result:** Execution ran with both SQLite and PostgreSQL Company/session storage and the PostgreSQL durable queue. Duplicate submission returned the first run; the Task reached In review and history/attention matched. No live model calls were made.

---

Final validation on the rebased code: **6,654 passed, 7 skipped** across the
complete database, OS and agents unit suites; **396 passed, no skips** across
Company integrations and execution/Task routes on all four adapters. The two
separate-process restart tests pass through both ordinary session history and
Company history/individual-run routes. Format and validation passed with output
read; mypy checked 1,146 framework and 21 CLI files without errors.

## Cascading archive and counts — October 16, 2026

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` with the cascading archive and grouped counts changes.

**Result:** All assertions passed without model calls. Temporary local SQLite databases only.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` with the cascading archive and grouped counts changes.

**Result:** All assertions passed without model calls. Temporary local SQLite databases only.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` with the cascading archive and grouped counts changes.

**Result:** All assertions passed without model calls. Temporary local SQLite databases only.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` with the cascading archive and grouped counts changes.

**Result:** All assertions passed without model calls. Temporary local SQLite databases only.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` with the cascading archive and grouped counts changes.

**Result:** All assertions passed without model calls. Temporary local SQLite databases only.

---

### 07_cascading_archive.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_cascading_archive.py` with the cascading archive and grouped counts changes.

**Result:** All assertions passed without model calls. Both SQLite and `--postgres` modes passed, each exercising sync and async managers: active-work refusal, Backlog move, cascade provenance, hidden children, counts, and exact restore.

---

## Cascading archive rebase verification — October 16, 2026

### 01_manage_products.py through 06_execute_tasks.py

**Status:** PASS

**Description:** Reran all six existing examples after rebasing onto the merged Task execution implementation. The execution example passed with SQLite and `COMPANY_DB=postgres`.

**Result:** All assertions passed without model calls. Duplicate execution retained its original run and attention reported one Task awaiting review.

---

### 07_cascading_archive.py

**Status:** PASS (initial rebase run failed; corrected and rerun)

**Description:** Main now validates registered executors when accepting a Task. The first rebase run failed with `Task executor is missing from the registry`; the example now supplies a registered writer without invoking it.

**Result:** SQLite and `--postgres` both passed, exercising both manager variants, active-work refusal, same-Product moves, cascade provenance, hidden children, grouped counts and exact restore.

---

## Archive review corrections — October 16, 2026

### 07_cascading_archive.py

**Status:** PASS

**Description:** Added a standalone Task archive/restore round trip after acceptance and asserted that its lifecycle history is unchanged.

**Result:** SQLite and `--postgres` passed with both sync and async managers, including the existing active-work refusal, cascade, counts and exact-restore checks. No model calls.

---
## Heartbeat overnight release fixes — October 16, 2026

Validated with PR 4 through `1f05cdacb0`, merged without rewriting published history.

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` using the development Python environment.

**Result:** Product CRUD, ownership, soft deletion and restore.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` using the development Python environment.

**Result:** Project lifecycle and Product containment.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` using the development Python environment.

**Result:** Registry-backed acceptance and Task transitions with human provenance.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` using the development Python environment.

**Result:** Sync/async wiki and decision-log operations.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` using the development Python environment.

**Result:** Product Manager construction and bounded tool publication; no provider call.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` using the development Python environment.

**Result:** SQLite and PostgreSQL modes with the real PostgreSQL durable queue; execution, duplicate starts, persisted results, run history and attention.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py` using the development Python environment.

**Result:** Declarations/restart, Sources, explicit evidence-backed Intake, stable deduplication, scheduler-backed Routines and history; no provider or outbound messaging call.

---

### Heartbeat release regressions

**Status:** PASS

**Description:** Reader errors from missing roots, Markdown, websites and Git run through the actual scheduler and durable queue, with stored executor ERROR results, failed Routine history and failed attention. Tests cover all template Product messages, Source permission confinement, company-wide Routine reads, owner-only writes, setup conflict/recovery, automatic custom-executor interfaces, Task origins, Summary narrative, changes and failed-Task detail.

**Result:** 454 Company/scheduler integrations passed without skips on sync/async SQLite and PostgreSQL, plus the existing MongoDB scheduler and filesystem transaction cases. All eight cookbook invocations passed. Formatting and validation passed; full output read, including zero mypy errors in 1,153 framework files and 21 CLI files. No live provider or outbound messaging calls.

Full `tests/unit/db`, `tests/unit/os` and `tests/unit/scheduler`: **6,285 passed, 47 skipped**. Redis availability was evaluated before its test container started; rerunning the complete generation-fence file with Redis available passed **19 tests, no skips**, resolving all eight Redis skips. The remaining 39 skips are optional drivers/mocks, root-only behavior and absent live-model credentials.

The separate main fix for tool arguments, async database identity and the Product Manager route was still unpublished and unmerged at validation time; integration remains pending. No published history was rewritten.

## Additional Heartbeat review fixes — October 16, 2026

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` using the development Python environment.

**Result:** Product CRUD, ownership, soft deletion and restore.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` using the development Python environment.

**Result:** Project lifecycle and Product containment.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` using the development Python environment.

**Result:** Registry-backed acceptance and Task transitions.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` using the development Python environment.

**Result:** Sync/async wiki and decision-log operations.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` using the development Python environment.

**Result:** Product Manager construction and bounded tool publication without provider calls.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` using the development Python environment.

**Result:** Both SQLite and PostgreSQL modes passed with the real durable queue, including history and attention.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py` using the development Python environment.

**Result:** Observed evidence hashes are supplied on Intake; rereading changed evidence still returns the original deduplicated Task. Declarations, schedules and restart checks passed.

---

### Authorization filtering, observed evidence and Routine validation

**Status:** PASS

**Description:** Reproduced all three reported defects on published head b6f9e74e0c. The same probes now show pause/resume omitting saved claims, invalid composed Routine names returning 422, and stale evidence rejected with zero Tasks created. Regression coverage retains saved claims in storage, checks owner writes and cross-user non-isolated responses, validates the 255-character boundary and setup before writes, and checks stale/missing/mismatched evidence hashes across all four SQL adapters.

**Result:** 466 focused Company/scheduler tests and 458 full Company/scheduler integrations passed, including SQLite/PostgreSQL sync and async adapters. All eight cookbook invocations passed. Format and validate passed; complete output read, including zero mypy errors in 1,153 framework files and 21 CLI files. No live model or outbound messaging calls.

Full database/OS/scheduler unit suites: **6,297 passed, 39 skipped**. Skips require optional drivers/mocks, root-only behavior or live-model credentials. No test failed.

## Bounded reader, delivery baseline and Routine proposals — October 16, 2026

### Focused regressions

**Status:** PASS

**Description:** Confined index paging without document reads, bounded Unicode fragments, selected-only Intake verification, failed-delivery recovery against the last delivered baseline, and denial of plain Routine proposals at tool/service/actual scheduler execution boundaries.

**Result:** 290 focused Company tests plus 16 targeted cases passed on all four SQL adapters. Compilation passed. An actual 1,149-file repository index returned 20 entries in 2,666 bytes; a selected os/app.py read returned 8,620 bytes with 8,000 content characters and continuation. Broader checks follow the implementation push.

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` in the development Python environment.

**Result:** Product CRUD, ownership, deletion and restore.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` in the development Python environment.

**Result:** Project lifecycle and Product containment.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` in the development Python environment.

**Result:** Human-created Task transitions and acceptance.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` in the development Python environment.

**Result:** Sync/async wiki and decision-log operations.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` in the development Python environment.

**Result:** Product Manager construction and bounded tools, without provider calls.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` in the development Python environment.

**Result:** SQLite and PostgreSQL modes passed with the real durable queue, results, history and attention.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py` in the development Python environment.

**Result:** Paged discovery, selected document reads and observed hashes, repeat-scan deduplication, declarations and scheduler-backed Routines.

---

### Post-push checks

**Status:** PASS

**Description:** Ran formatting and validation after the implementation push. Corrected one mypy narrowing error in configured-path selection, then reran both scripts and read their complete output.

**Result:** Zero mypy errors in 1,153 framework and 21 CLI files; lint and cookbook pattern checks passed. All 478 Company/scheduler integrations passed on SQLite/PostgreSQL sync and async plus existing scheduler/filesystem cases, without skips. The final reader/authority/delivery regression selection passed 32 tests. All eight cookbook invocations passed. No provider or outbound messaging calls.

Full database/OS/scheduler unit suites: **6,303 passed, 39 skipped**. Skips require optional drivers/mocks, root-only behavior or live-model credentials. No test failed.


## Inherited main release-fix validation

### 01_manage_products.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/01_manage_products.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/02_manage_projects.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/05_product_manager.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

---


## Final merged-main validation — October 16, 2026

**Status:** PASS

**Description:** Integrated merged main PR #11112 (c0731293a8) with a normal merge, preserving the published PR 6 ancestry. Retained Routine proposal denial and applied main's nullable/empty-argument contract to Source discovery, selectors and content pagination. Updated Gemini's expected integer parameter list for the new offsets.

**Result:** Full database/OS/scheduler units: **6,315 passed, 39 skipped** (optional drivers/mocks, credentials and root-only behavior). Company/scheduler integrations: **447 passed**, including SQLite/PostgreSQL sync and async plus restart coverage; filesystem transaction regressions: **33 passed**; no integration skips. Tool/schema/Gemini regressions: **290 passed**. All eight cookbook invocations passed again, covering each file listed above and PostgreSQL execution. Final format and validate passed with complete output read: no mypy errors in 1,153 framework and 21 CLI files. No provider or outbound messaging calls.


## Heartbeat rebase, completion and retention — October 16, 2026

Rebased onto PR 4 ad213020cf, preserving main PR #11112 and the latest execution fixes. Published the authorized rebase once at 7d2758d0f4; all later changes use normal commits. Before the rebase push, 312 Company regressions and format/validate passed.

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` in the development environment.

**Result:** Product lifecycle and the default archive policy. No live model or outbound messaging calls.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` in the development environment.

**Result:** Project transitions, including the terminal-Task completion guard. No live model or outbound messaging calls.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` in the development environment.

**Result:** Task lifecycle and acceptance. No live model or outbound messaging calls.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` in the development environment.

**Result:** Sync/async wiki and decision-log APIs. No live model or outbound messaging calls.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` in the development environment.

**Result:** Product Manager routing and bounded tools without maintenance or outbound delivery. No live model or outbound messaging calls.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` in the development environment.

**Result:** SQLite and PostgreSQL execution through the durable queue, run history and attention. No live model or outbound messaging calls.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py` in the development environment.

**Result:** Bounded Source reads, deduplicated Intake, Refresh completion proposals, old-work archival and restore. No live model or outbound messaging calls.

---

Final suite results follow below. The first integration pass exposed five legacy metadata assertions; these now expect the required default archive_window_days=14, while preserving unrelated metadata.

### Final completion and retention validation

**Status:** PASS

**Description:** Full database, OS and scheduler unit suites; Company and scheduler integrations on SQLite and PostgreSQL with sync/async adapters; process restart, durable execution and filesystem transaction regressions. Added 52 archive/completion/order integration cases, including exclusion of archived Task details from completion proposals and executor context.

**Result:** **6,317 unit tests passed, 39 skipped** for unavailable optional dependencies, credentials and environment-specific behavior. **544 integration tests passed with no skips.** All eight cookbook invocations passed again after the final change. The initial five integration and two unit failures were legacy metadata assertions; these now include the required default archive window while retaining existing metadata. Final format and validate passed; complete output was read, including mypy success for 1,154 framework and 21 CLI files. No live model or outbound messaging calls.

---


## Heartbeat on cascading archives — October 16, 2026

Rebased onto PR #11114 at 7962abc7f6, including merged Task execution on main at 9d3634e922. Published the requested rebase at 877943e581 after 158 SQLite/focused tests passed (84 PostgreSQL cases deferred to the full run). Subsequent updates use normal commits. PR 4.5 owns cascade transactions, grouped counts, exact restore and ancestor visibility; Heartbeat adds age checks inside that transaction and retains parent locking for Intake deduplication.

The first SQLite run found eight inherited archive-fixture failures because the writer was not registered. PR 4.5 published its fixture correction during the rebase; incorporating that commit resolved all eight. The first wider/cookbook attempt was blocked by sandbox localhost permissions; the rerun uses the existing local database services.

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` against the rebased implementation.

**Result:** Product lifecycle and metadata defaults. All assertions passed; no live model or outbound messaging calls.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` against the rebased implementation.

**Result:** Project lifecycle and completion validation. All assertions passed; no live model or outbound messaging calls.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` against the rebased implementation.

**Result:** Task lifecycle and executor acceptance. All assertions passed; no live model or outbound messaging calls.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` against the rebased implementation.

**Result:** Wiki and decision APIs. All assertions passed; no live model or outbound messaging calls.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` against the rebased implementation.

**Result:** Product Manager configuration and bounded tools. All assertions passed; no live model or outbound messaging calls.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` against the rebased implementation.

**Result:** SQLite and PostgreSQL Company execution through the durable queue; duplicate execution and attention. All assertions passed; no live model or outbound messaging calls.

---

### 07_cascading_archive.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_cascading_archive.py` against the rebased implementation.

**Result:** SQLite and PostgreSQL cascade/refusal/counts/exact-restore behavior, with sync and async managers. All assertions passed; no live model or outbound messaging calls.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py` against the rebased implementation.

**Result:** Declarations, bounded Source reads, Intake deduplication, Refresh completion proposals and retention. All assertions passed; no live model or outbound messaging calls.

---

### Final validation on the cascading-archive base

**Status:** PASS

**Description:** Full database/OS/scheduler unit suites and Company/scheduler integrations on SQLite/PostgreSQL sync and async, including cascade and retention composition, durable execution, restart and filesystem transactions.

**Result:** **6,317 unit tests passed, 39 skipped** (optional Firestore/asyncpg dependencies, credentials and root-only behavior). **620 integration tests passed, no skips**, including 12 new cascade/retention/deduplicated-insert cases. All ten cookbook invocations passed. Format and validate passed with complete output read; exact-tree validation also passed after excluding unrelated formatter changes. Mypy checked 1,155 framework and 21 CLI files. Tests/cookbooks used the development Python 3.12 environment; validation used the existing clean Python 3.10 environment. `git diff --check` passed. No live model calls or outbound messages.

---
