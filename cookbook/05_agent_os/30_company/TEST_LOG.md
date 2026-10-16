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

### Automation cookbook regression — October 16, 2026

**Status:** PASS

**Description:** Ran all seven files in `cookbook/05_agent_os/30_company/`
with the Python 3.12 development environment:

- `01_manage_products.py`: Product CRUD and lifecycle assertions passed.
- `02_manage_projects.py`: Project lifecycle and Product ownership assertions passed.
- `03_manage_tasks.py`: Task acceptance and lifecycle assertions passed.
- `04_manage_playbook.py`: wiki persistence and version-conflict checks passed.
- `05_product_manager.py`: proposal, status, and decision tools passed.
- `06_execute_tasks.py`: manual start passed on SQLite and PostgreSQL.
- `07_heartbeat.py`: Routine, Source, and rehydration assertions passed.

**Result:** Ten executions passed, including two additional runs of
`06_execute_tasks.py` with `COMPANY_AUTOMATION=1`, once with SQLite Company
storage and once with `COMPANY_DB=postgres`. Both used the real PostgreSQL
durable queue and application scheduler lifespan. A human-accepted Ready Task
was picked up without a start request; a Routine proposal with verified Source
evidence was automatically accepted using the built-in `has_source_evidence`
and `executor_registered` checks, then executed to In review. The example
revoked the authorization and cleaned up its temporary schema. No application
check registration, provider calls, or external messages were needed. SQLite
retains its documented development-only session fallback.

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

### Automation final validation — October 16, 2026

**Status:** PASS

**Description:** Validated Automation with Heartbeat head
`c1f7f0b1909c9660e755b26e298650b99ee480b7` incorporated. The full
`libs/agno/tests/unit/db`, `libs/agno/tests/unit/os`, and
`libs/agno/tests/unit/scheduler` suites passed **6,312 tests**. Fifteen
conditional skips cover optional Firestore/Mongo/MySQL test dependencies, a
root-only test, live OpenAI tests, and Redis-only stream-fencing tests.

**Result:** All Company and scheduler database integration files passed
**359 tests** on sync/async SQLite and PostgreSQL. Four optional MongoDB
scheduler cases were skipped; no requested SQLite/PostgreSQL cases were skipped.
The scheduler HTTP owner-recheck integration file passed **6 tests**. The ten
cookbook executions listed above were rerun successfully on the merged code.
Compilation, the full format script, and validation passed; both mypy summaries
(1,155 Agno files, 21 agnoctl files) and the full validation output were read.
Unrelated formatter changes were excluded and validation passed again on the
exact feature tree. Tests/cookbooks used Python 3.12 and validation used the
clean Python 3.10 development environment.

Regressions cover two concurrent claims, interrupted dispatch before and after
queue submission, queued withdrawal, executor mismatch, revoked authorization,
built-in checks without application registration, unknown checks with recorded
reasons, forged Source evidence, scope/check races, and lifetime limits.
Payload authority injection and internal-token-only Task submission are denied.
Self-review reproduced a Routine Project proposal regression on all four
adapters; its fix and the complete integration rerun passed. No live provider
calls or outbound messages were made.

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

### Automation after final Heartbeat integration — October 16, 2026

**Status:** PASS

**Description:** Incorporated the final Heartbeat head
`7404f7f9c0b8deb89b1ff35d47aca4886163574c`, including main's filesystem
transaction fixes and the initial Task schema without unreleased migrations.
The final parent update changed only this log and already-applied formatting.

**Result:** Reran the full DB/OS/scheduler unit suites: **6,320 passed,
7 conditional skips** for optional backend test dependencies, root-only and
live-provider tests. Redis fencing tests ran and passed in this rerun. The
combined integration run passed **398 tests**: 359 Company/scheduler database
cases, six scheduler owner checks and 33 inherited filesystem transaction
regressions. Four optional MongoDB cases were skipped; all SQLite/PostgreSQL
cases ran. All ten cookbook executions passed again. Full format and validation
passed, including mypy on 1,153 core and 21 CLI files; output was read.
Unrelated formatter-only edits were excluded and exact-tree validation passed.
No live provider calls or outbound messages were made.

---

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

### Automation managed-role review fix — October 16, 2026

**Status:** PASS

**Description:** Reproduced automatic pickup's managed-role 403 with isolation
both enabled and disabled. The Task run route now checks the restored accepting
human's current executor permission before reserving work. Four regressions
cover successful pickup without a scheduler-principal grant and revocation
between transport admission and Task reservation. All 27 execution router tests
passed; the combined Company unit selection passed 51 tests.

Integrated Heartbeat through `65af6a10a698603232ae98056b49baeb955e4dca`
with normal merge commits. Explicit, evidence-backed intake retains proposed
executor and Project fields and trusted Routine lineage. Added coverage on all
four SQL adapters for those fields and cross-Product rejection. The execution
cookbook now uses canonical evidence links returned by the Source reader.

**Result:** Full DB/OS/scheduler unit suites passed **6,329 tests, 7 conditional
skips** (optional mockfirestore, mongomock and aiomysql dependencies, one root-only
test and three live-provider tests). The first attempt encountered eight Redis
connection failures when the shared service stopped; the complete rerun passed
with dedicated temporary Redis and MongoDB services. Telebot-dependent tests ran.

After the final two-line parent Source-existence guard, reran all Company units
and the complete integration selection: **457 passed**, comprising **51 Company
unit tests and 406 integrations**, with four optional MongoDB scheduler skips.
Every requested sync/async SQLite/PostgreSQL case ran, including scheduler owner
checks and 33 filesystem transaction cases.

All ten cookbook executions passed again on the final parent:

- `01_manage_products.py`: PASS — Product lifecycle and isolation.
- `02_manage_projects.py`: PASS — Project lifecycle.
- `03_manage_tasks.py`: PASS — Task lifecycle and accepted scope protection.
- `04_manage_playbook.py`: PASS — Sync/async wiki edits and stale-write rejection.
- `05_product_manager.py`: PASS — Backlog proposal, status and decision.
- `06_execute_tasks.py`: PASS — SQLite and PostgreSQL manual execution;
  SQLite and PostgreSQL automatic pickup, bounded acceptance and revocation.
- `07_heartbeat.py`: PASS — Explicit proposal deduplication and paused scheduling.

The first automation cookbook attempt after the intake API update rejected a
noncanonical temporary-file URI. Using the reader's returned evidence links
fixed it; all ten executions passed on rerun. Format and validation passed with
all output read (mypy: 1,153 core and 21 CLI files). Unrelated formatter changes
were excluded and exact-tree validation repeated. No live provider calls or
outbound messages were made.

---

## Automation release follow-up — October 16, 2026

Validated after rebasing onto Heartbeat `fb9592b2a3`, including Execution
`1f05cdacb0` and the published main fix `286626fb10`. The main fix remains a
separate open dependency. Follow-up corrections are normal commits; the requested
rebase preserves their separation. No tables or routes were added by Automation.

### 01_manage_products.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/01_manage_products.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

**Description:** Product lifecycle, ownership and restoration.

**Result:** Completed assertions using the development Python environment.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/02_manage_projects.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

**Description:** Project lifecycle and Product containment.

**Result:** Completed assertions.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

**Description:** Task lifecycle, registry-backed acceptance and protected accepted scope.

**Result:** Completed assertions.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Re-ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` in the isolated development environment for the October 16 release fixes.

**Result:** Exit 0; completed all assertions without model calls.

**Description:** Sync/async wiki and decision operations, including stale writes.

**Result:** Completed assertions.

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

**Description:** Bounded Product Manager tools and its ordinary HTTP route.

**Result:** Completed assertions without a provider call.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran manual execution on SQLite and PostgreSQL, then automatic
pickup and bounded acceptance on both databases. All use the real PostgreSQL
durable queue. Explicit Intake proposals carry hashes from the preceding Source
read. Automatic policies include expiry and use built-in checks.

**Result:** All four invocations passed: execution, duplicate submission, result
projection, automatic acceptance/pickup and revocation. No provider calls.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Source reads, observed evidence, explicit proposal deduplication,
Routine declarations, restart and paused scheduling.

**Result:** Completed assertions. All ten cookbook invocations passed overall.

---

### Final Company and scheduler regression suites

**Status:** PASS

**Description:** Required expiry and default server check; content-only policy
fingerprints; distinct-Task budgets per policy version; saved accepting identity;
concurrent scheduler claims and interrupted submissions; revoked and withdrawn
work; exclusion of registry-only SchedulerTools executors. The authenticated
Intake fixture calls the real Source-read and proposal tools, passes their hashes,
omits executor selection through null/empty model arguments, and verifies exactly
one writer execution as Alice through the real queue on all four SQL adapters.

**Result:** Full DB/OS/scheduler units: **6,354 passed, seven conditional skips**
(optional mockfirestore, mongomock, aiomysql, root-only behavior and three
live-provider cases). Redis fencing tests ran. Company/scheduler database integrations, scheduler
HTTP owner checks, stable database restart checks and filesystem regressions:
**524 passed, four optional MongoDB cases skipped**. Every SQLite/PostgreSQL
sync/async case ran. Nullable tool schema/argument regressions: **26 passed**.
Full format and validate passed; all output read (mypy: 1,153 core files and
21 CLI files). Unrelated formatter edits were excluded and exact-tree validation
passed again. Intermediate rebase failures exposed the changed enqueue-first
boundary and Source pagination optionals; the final runs include both repairs.

---

### Overnight release probes

**Status:** FAIL — mixed outcomes retained below; targeted Automation regressions pass.

**Description:** Ran the original behavioral probe scripts unchanged, then
compatible copies against the final integration. Used the original PostgreSQL
URL on localhost:5532 with database `ai_claude`, authority capture port 8161,
and performance port 8110. Original report evidence was preserved. Compatibility
changes supply required policy expiry, explicit Intake proposals with observed
hashes, and the existing SchedulerTools `cron` argument. No assertion was relaxed.
Retired migration calls were omitted only from the compatible registration probe.

| Probe | Result on compatible harness |
| --- | --- |
| A identity/scopes | 223/225 pass. The two remaining assertions expect Routine create/resume without executor run permission; both correctly receive 403 under the scheduler's existing rule. |
| C isolation | 54/55 pass. The subject-less token read still returns 200; this shared read behavior remains outside the Automation fixes. |
| D disabled/registration | 15/16 pass, including unsupported InMemoryDb routes, custom table names, and two fresh-schema processes. Its MongoDB probe targets unavailable port 1 and cannot run. |
| D main-disabled export | Completed; disabled Company has no Company routes or tables. |
| D2 legacy migration | Not applicable: imports retired, unreleased migration modules. The original script fails with ImportError; this is not counted as a pass. |
| E concurrency | 14/14 pass, with 20 rounds per race across SQLite/PostgreSQL sync/async. |
| E2 async concurrency | 6/6 pass. |
| F authority | 19/21 pass. Two payload-shape expectations remain over-strict relative to the existing scheduler payload contract; they do not demonstrate widened executor authority. |
| F2 scheduler fence | Executor and Routine schedule creation both raise PermissionError; no schedule is written. |
| G setup/fingerprint | Existing-deployment setup returns 409; all three fingerprint comparisons are true, including fresh-token instructions and identical-policy PATCHes. |
| Product Manager route | Ordinary GET route returns 200. |

The unchanged A/G scripts omit the newly required expiry; D/D2 use retired
migration APIs; E/E2 omit the explicit Intake proposal; F uses the wrong scheduler
argument. These original failures were recorded before the compatibility rerun.
The registration probe covers Company-off mounting; the new HTTP regression
separately proves Company-on exclusion of SchedulerTools agents and nested teams
and workflows.

The supplied performance app/driver seeded 50 Products, 500 Projects, 5,000 Tasks
and 200 wiki pages. All ten read timing checks passed; all ten workflow starts
were independently confirmed In review. The live-model Intake trigger failed
with `OPENAI_API_KEY not set`, so live-model performance is not validated. The
export/report helper scripts depend on the original report snapshots and are not
behavioral probes. Local probe services started for this run were stopped.

---


### Async acceptance-history typing review — October 16, 2026

**Status:** PASS for the two reported diagnostics and focused regressions.

**Description:** Reproduced both unannotated `prior` diagnostics on `ee30f46c05`
with the repository Python 3.12 environment. Both async SQL adapters now annotate
the scalar query result as a sequence of nullable Task transition lists. Runtime
queries and acceptance accounting are unchanged.

**Result:** Eight acceptance-budget regressions passed across sync/async SQLite
and PostgreSQL. The same Python 3.12 validation invocation decreased from 35 to
33 diagnostics; comparison confirms only the two `prior` errors disappeared,
with no new diagnostics. The remaining 33 unrelated diagnostics prevent that
environment's full validation from passing. Full formatting passed, and full
validation passed in the clean Python 3.10 environment used for this PR (1,153
core files and 21 CLI files). Complete output from both environments was read.
Unrelated formatter changes were excluded.

---


### Automation review follow-up — October 16, 2026

**Status:** PASS for the four requested fixes and regressions.

**Description:** Exhausted policies now stop before Source IO and custom checks,
while the existing transaction still serializes acceptance budgets. Source bounds
and the built-in evidence check share one fresh read. Runtime automation schedules
refuse public mutation through REST and sync/async scheduler management. Candidate
queries filter active Task states before paging. Generic schedule payload updates
validate executor registration and check names before saving human authority.

**Result:** 6,495 tests passed with seven conditional skips across the complete
unit/db, unit/os and unit/scheduler suites plus the affected Company/SchedulerTools
tests. Company, Task/Product/Project, scheduler and owner-check integrations passed
509 tests on SQLite/PostgreSQL, including sync/async adapters and the real durable
queue; four optional MongoDB cases skipped. The focused 32 acceptance/pickup
regressions and 32 authorization tests passed separately. Tests prove zero Source
reads for exhausted policies over three ticks and a restart, renewed acceptance
after policy changes, retry after server facts recover, internal schedule refusal
without breaking ordinary Routine pause/resume, exclusion of terminal history,
and 422 validation without losing the 403 run-permission boundary.

Full format and validate scripts passed in the clean Python 3.10 environment
(1,153 core files and 21 CLI files); output was read and unrelated formatter edits
were excluded. Tests used the worktree Python 3.12 environment. That environment's
full validation still fails on existing provider/dependency diagnostics: a fresh
cache comparison against 93ba14535b produced the same 53 diagnostics on both trees,
with none added or removed. The initial cached invocation reported one additional
BigQuery import diagnostic, absent in both fresh comparisons. This worktree's
installed dependencies differ from the separate Python 3.12 environment used in
the earlier 33-diagnostic review.

---

### 06_execute_tasks.py — automation review follow-up, SQLite

**Status:** PASS

**Description:** Ran `COMPANY_AUTOMATION=1 .venv/bin/python cookbook/05_agent_os/30_company/06_execute_tasks.py`.

**Result:** The real scheduler picked up Ready work and accepted one verified
Routine proposal through the durable queue. Tasks reached In review, and revocation
blocked further acceptance. Offline execution made no model call.

---

### 06_execute_tasks.py — automation review follow-up, PostgreSQL

**Status:** PASS

**Description:** Ran `COMPANY_AUTOMATION=1 COMPANY_DB=postgres .venv/bin/python cookbook/05_agent_os/30_company/06_execute_tasks.py`.

**Result:** The same automatic pickup, bounded acceptance and revocation behavior
passed using PostgreSQL records, run storage and the durable queue, without model calls.

---


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

## Heartbeat Task restore follow-up — October 16, 2026

Integrated PR #11114's pinned b7c73d7a566b9906122cfad5822151e1fa921464 as normal merge 9aadb8feb2. The previous rebase was already published; no history was rewritten. All four adapters retain task_restore_fields: ordinary Task restore preserves acceptance history, recorded cascade archives receive matching restore events, and queue acceptance revocation remains enforced. Cascade provenance, counts, ancestor filtering and Heartbeat retention are preserved.

Publication checks: 103 SQLite/focused tests passed, with PostgreSQL deferred to the full integration run; format and exact-tree validate passed with output read.

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` on the integrated restore fix.

**Result:** Product lifecycle and archive policy defaults. All assertions passed without live model or outbound messaging calls.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` on the integrated restore fix.

**Result:** Project lifecycle and completion guards. All assertions passed without live model or outbound messaging calls.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` on the integrated restore fix.

**Result:** Task lifecycle and registered executor acceptance. All assertions passed without live model or outbound messaging calls.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` on the integrated restore fix.

**Result:** Wiki and decision APIs. All assertions passed without live model or outbound messaging calls.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` on the integrated restore fix.

**Result:** Product Manager construction and bounded tools. All assertions passed without live model or outbound messaging calls.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` on the integrated restore fix.

**Result:** SQLite and PostgreSQL durable execution, duplicate runs and attention. All assertions passed without live model or outbound messaging calls.

---

### 07_cascading_archive.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_cascading_archive.py` on the integrated restore fix.

**Result:** SQLite and PostgreSQL cascades, grouped counts, exact restore and unchanged ordinary Task acceptance history. All assertions passed without live model or outbound messaging calls.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py` on the integrated restore fix.

**Result:** Source reads, deduplicated Intake, completion proposals and retention. All assertions passed without live model or outbound messaging calls.

---

### Final Task restore validation

**Status:** PASS

**Description:** Full database/OS/scheduler units and Company/scheduler integrations on SQLite/PostgreSQL sync and async, including queued/running archive-restore acceptance, genuine acceptance revocation, cascades, counts, retention and restart.

**Result:** Final full unit rerun: **6,317 passed, 39 dependency/environment skips**. Integrations: **652 passed, no skips**. All ten cookbook invocations passed. The first unit run had one failure in the unchanged Redis real-clock TTL test (`test_true_ttl_expiry_reseeds`: keys had not expired after 1.2 seconds); its isolated module rerun passed all 48 tests, then the complete unit rerun passed without code changes. Format and exact-tree validation passed with full output read (mypy: 1,155 framework and 21 CLI files). `git diff --check` passed. No live model or outbound messaging calls.

---





## Automation completion and current Heartbeat rebase — October 16, 2026

Rebased Automation onto Heartbeat `b919bc8581`, which contains Execution
`ad213020cf` and merged main PR #11112. Retained the parent's bounded Source
reader, Routine Intake fence, nullable tool schemas, run-recovery assertions,
terminal-Task lifecycle gate, archive behavior and sorting. Automation adds the
explicit `complete_projects` permission through the existing policy boundary.
Refresh remains proposal-only; accepted Project completions share the policy's
checks, expiry and distinct-work budget with Task acceptance.

### Required suites and validation

**Status:** PASS.

**Description:** Tested permission admission and managed-role revocation before
and during checks in both isolation modes; Refresh proposal matching; all-terminal
Tasks including archived records; Source/scope/check/expiry/revocation failures;
Task/Project budget races; and executor-less authenticated Intake through the real
queue under concurrent scheduler ticks on all four SQL adapters.

**Result:** The complete DB/OS/scheduler unit suites plus Company/SchedulerTools
passed **6,515 tests, seven conditional skips** (optional mockfirestore,
mongomock and aiomysql dependencies, a root-only test and three live-provider
tests). An initial full run had one unrelated fakeredis TTL timing failure;
its entire module then passed 48 tests, and the complete full-suite rerun passed.
No Company case failed. The 64 focused tests passed, followed by 46 policy and
completion cases after preserving legacy Task-only fingerprints when the new
permission is omitted/false. The fingerprint release probe passed again.
The complete Company/scheduler integration
selection passed 627 tests; four PostgreSQL scheduler parity cases initially
skipped because their URL variable was unset. Rerunning that parity file with
`AGNO_TEST_POSTGRES_URL` passed eight tests (four SQLite repeats plus all four
PostgreSQL cases), giving **631 distinct passing integration cases**. Four optional
MongoDB cases remain skipped because `AGNO_TEST_MONGO_URL` was unset. No requested
SQLite/PostgreSQL case remained skipped. The selection includes lifecycle CRUD,
archive, real-queue execution, stable database restart and scheduler owner checks.

Both full format and validate scripts passed; complete output was read. Validation
reported no errors in 1,154 framework files and 21 CLI files. Unrelated formatter
edits were excluded and validation passed again on the exact feature tree. Tests
and cookbooks used Python 3.12; validation used the clean Python 3.10 environment.

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py`. Product lifecycle, ownership and restore.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py`. Project lifecycle and Product containment.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py`. Task acceptance, frozen scope and lifecycle.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py`. Sync/async wiki and decision operations with version checks.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py`. Product Manager tools without provider calls.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 06_execute_tasks.py — SQLite manual

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py`. Real durable-queue execution, duplicate submission, results and history.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 06_execute_tasks.py — PostgreSQL manual

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py`. The same manual execution contract with PostgreSQL Company records.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 06_execute_tasks.py — SQLite automation

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py`. Ready pickup and evidence-backed automatic acceptance through the real queue; human Task review followed by Refresh proposing and the authorized tick completing the Project.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 06_execute_tasks.py — PostgreSQL automation

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py`. The same pickup, acceptance, revocation and explicitly authorized Project completion with PostgreSQL records and queue.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py`. Bounded Source reads, deduplicated Intake, completion proposals, archival and restore; Refresh itself never accepts or completes work.

**Result:** All assertions passed without model calls or outbound messaging.

---

### Claude release probes on the rebased branch

**Status:** MIXED — exact outcomes retained, not treated as an all-pass result.

**Description:** Ran the original behavioral scripts unchanged and documented
compatibility copies against this branch using the original PostgreSQL database
`ai_claude` on localhost:5532, capture port 8161 and performance port 8110. Original
reports were preserved. Compatibility changes supply mandatory expiry, explicit
Intake proposals with observed hashes, and SchedulerTools' `cron` argument. The
updated authority probe additionally tests that plain Routine proposals are
refused, then uses the real evidence-backed Intake tool for its unchanged lineage
assertion. Payload/authority assertions were not relaxed.

| Probe | Result |
| --- | --- |
| A identity/scopes | Original 222/225; compatible 223/225. Mandatory expiry explains the original extra 422. Remaining expectations omit the executor run permission required to create/resume a Routine and correctly receive 403. |
| C isolation | 54/55. Subject-less token reads still return 200; this existing shared read behavior is outside Automation. |
| D disabled/registration | Compatible 15/16, including custom tables and fresh-process registration. The MongoDB probe targets unavailable port 1. Original stops at retired migration imports. |
| D main-disabled | Completed; no Company routes or tables when Company is disabled. |
| D2 legacy migration | Inapplicable: imports retired, unreleased migrations. Both copies fail with ImportError; not counted as passing. |
| E concurrency | Compatible 14/14, retaining 20 rounds per race. Original requires the current explicit Intake proposal argument. |
| E2 async concurrency | Compatible 6/6; same original Intake signature mismatch. |
| F authority | Updated compatible 20/22. Original and the first compatibility copy stop at the parent's new plain-Routine-proposal fence. The final copy passes that denial and Intake lineage; two existing payload-shape assertions still fail without demonstrating widened authority. |
| F2 scheduler fence | Both executor and Routine mutations raise PermissionError; no schedule is written. |
| G setup/fingerprint | Compatible setup returns 409 and all three fingerprint comparisons are true. Original omits mandatory expiry. |
| Product Manager route | Ordinary GET returns 200. |

The supplied performance driver seeded 50 Products, 500 Projects, 5,000 Tasks and
200 wiki pages. Read checks completed and all ten workflow starts were independently
confirmed In review through the adapter. Live-model Intake failed with
`OPENAI_API_KEY not set`; no live-model performance claim is made. The temporary
server and uniquely named performance schema were cleaned up. Export/report
helpers depend on the original snapshots and are not behavioral probes.


## Automation on final Heartbeat and cascading archives — October 16, 2026

This is the final validation for Automation on Heartbeat `c51b1842e9`, including
cascading archives and grouped counts from PR #11114 and merged Task execution.
The parent versions of shared files are retained, including the subsequent standalone Task restore fix that preserves queued acceptance history. Automatic acceptance uses the
same Product hierarchy lock as archive; Project completion snapshots exclude
computed counts. Restored Tasks are re-read because cascade restore adds history.
The previous validation sections remain as history for their stated heads.

### Complete suites and validation

**Status:** PASS

**Description:** Ran the complete unit/db, unit/os and unit/scheduler suites plus
Company and SchedulerTools units. Ran all Company and scheduler integrations,
including execution/restart, playbook, heartbeat, cascades, retention, scheduler
ownership, lifecycle parity and SQLite adapter suites. PostgreSQL parity was
explicitly enabled; every requested SQLite/PostgreSQL case ran.

**Result:** 6515 passed, 7 skipped, 534 warnings in 423.58s (0:07:03). 739 passed, 4 skipped, 73 warnings in 287.79s (0:04:47). All 64 retention cases and the four
restore-retry regressions also passed independently. The first focused run had
460 passes and four fixture failures: the old retry test reused a Task snapshot
from before cascading archive/restore. The corrected test proves stale snapshots
are rejected and a fresh read succeeds. The final full integration run includes
that correction and PR 5's last 12 retention cases. A later run exposed a rebase
lock-order mistake in the existing stale-writer regression: an early lock blocked
manual competing writers. Manual transitions now retain the parent's original
lock timing; only automatic acceptance locks before its budget read. All 40 Task
lifecycle parity cases passed after the correction, before the final full rerun.
Format and validate passed, complete output read: no mypy errors in 1,155 framework
and 21 CLI files. Unrelated baseline formatter edits were excluded and the exact
PR tree validated. Tests/cookbooks used Python 3.12, validation clean Python 3.10.
A development Python 3.12 comparison found the identical 53 existing
mypy diagnostics in 13 files on parent and head, with no introduced diagnostics.
Neither async adapter has a prior annotation error.

---

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py`. Product CRUD, metadata, archive and restore.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py`. Project lifecycle and scope.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py`. Task lifecycle and accepted-scope guards.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py`. Versioned playbook, wiki, decisions and shared context.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py`. Product Manager setup, tools and read surface.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 06_execute_tasks.py — SQLite manual

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py`. Durable execution, duplicate submission and results/history.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 06_execute_tasks.py — PostgreSQL manual

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py`. The same manual execution contract with PostgreSQL records and queue.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 06_execute_tasks.py — SQLite automation

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py`. Automatic pickup, bounded Intake acceptance, human Task review and authorized Refresh completion.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 06_execute_tasks.py — PostgreSQL automation

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py`. The same automation contract with PostgreSQL records and queue.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 07_cascading_archive.py — SQLite

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_cascading_archive.py`. Sync/async hierarchy guards, grouped counts, cascading archive and exact restore.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 07_cascading_archive.py — PostgreSQL

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_cascading_archive.py`. The same sync/async hierarchy contract on PostgreSQL.

**Result:** All assertions passed without model calls or outbound messaging.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py`. Bounded Source reads, Intake deduplication, Refresh proposals, retention and restore; Refresh never accepts or completes work.

**Result:** All assertions passed without model calls or outbound messaging.

---

### Claude release probes on the final rebased runtime

**Status:** MIXED — individual failures and unavailable checks are retained.

**Description:** Reran the original scripts unchanged and the documented
compatibility copies using PostgreSQL `ai_claude` on localhost:5532, capture port
8161 and performance port 8110. Compatibility changes are limited to mandatory
expiry, explicit Intake/hash inputs, the current cron argument, retired migration
imports, and using Intake after proving the plain Routine proposal fence.

**Result:** A original 222/225, compatible 223/225; C 54/55; D compatible 15/16;
E 14/14; E2 6/6; F compatible 20/22; F2 denies both mutations; G rejects setup on
existing Products and all three fingerprint comparisons are true. The disabled
Company probe and Product Manager GET pass. The remaining A expectations omit
executor run scope; C retains the existing subject-less read behavior; D targets
unavailable MongoDB port 1; F's two payload-shape assertions do not demonstrate
widened authority. Original obsolete signatures and D2's retired migration imports
remain explicit non-passes, as detailed in the earlier probe table.

Performance seeded 50 Products, 500 Projects, 5,000 Tasks and 200 wiki pages. All
read checks completed; ten workflow Tasks were independently confirmed In review.
Live-model Intake failed because OPENAI_API_KEY was absent. The temporary server
and unique schema were cleaned up. These results do not claim a live-model pass.


## Main rebase and Heartbeat recovery — October 16, 2026

Rebased only the Heartbeat commits onto main at 17cf2e8b59, preserving the merged cascade/restore implementation. Published e9d5a76274 after 172 SQLite checks passed so the stacked automation branch could proceed. Later fixes use normal commits.

Summary delivery bookkeeping now lives in a separate versioned Product filesystem namespace; retention migrates legacy receipts before deleting reports. Routine creation remains disabled until linked and recovers the identical pending request in the scheduler creator name bucket. Explicit pauses prevent automatic retry activation.

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py` on the main rebase with the recovery fixes.

**Result:** Product lifecycle and archive window defaults. All assertions passed. No live model or outbound messaging calls.

---

### 02_manage_projects.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/02_manage_projects.py` on the main rebase with the recovery fixes.

**Result:** Project lifecycle and terminal-Task completion guard. All assertions passed. No live model or outbound messaging calls.

---

### 03_manage_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/03_manage_tasks.py` on the main rebase with the recovery fixes.

**Result:** Task lifecycle and registered executor acceptance. All assertions passed. No live model or outbound messaging calls.

---

### 04_manage_playbook.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/04_manage_playbook.py` on the main rebase with the recovery fixes.

**Result:** Versioned wiki and decision APIs. All assertions passed. No live model or outbound messaging calls.

---

### 05_product_manager.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/05_product_manager.py` on the main rebase with the recovery fixes.

**Result:** Product Manager construction and bounded tools. All assertions passed. No live model or outbound messaging calls.

---

### 06_execute_tasks.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/06_execute_tasks.py` on the main rebase with the recovery fixes.

**Result:** SQLite and PostgreSQL durable execution, duplicate runs and attention. All assertions passed. No live model or outbound messaging calls.

---

### 07_cascading_archive.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_cascading_archive.py` on the main rebase with the recovery fixes.

**Result:** SQLite and PostgreSQL cascades, grouped counts, exact restore and ordinary acceptance history. All assertions passed. No live model or outbound messaging calls.

---

### 07_heartbeat.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/07_heartbeat.py` on the main rebase with the recovery fixes.

**Result:** Bounded Source reads, deduplicated Intake, completion proposals and retention. All assertions passed. No live model or outbound messaging calls.

---

## Automation integration with current Heartbeat — October 16, 2026

Rebased onto Heartbeat `e9d5a76274` and published `3137d4fde1` after **282 SQLite
integration tests and 52 focused unit tests passed**. Full format and clean
validation passed with their output read. The five Automation commits replayed
unchanged; the new parent differed from the previously integrated parent only
in its validation log.

Heartbeat then published `ae9d9b933c`. Integrated it with a normal merge,
retaining deferred Routine activation, recovery of interrupted creation,
Summary delivery state outside retained reports, and all parent regression
tests. No history rewrite followed the initial rebase push.

### Authorized Routine creation recovery

**Status:** PASS

**Description:** Extended the parent's link/enable failure tests with an
`auto_accept` policy across SQLite and PostgreSQL, sync and async. The initial
SQLite run reproduced four policy-enabled retry failures (409), while four
ordinary Routine cases passed. Recovery now compares the human request without
server-generated grant fields and saves newly checked human authority.

**Result:** **211 focused integration/router tests passed**, followed by **two
additional authenticated retry tests** covering isolation on and off. A retry
without `tasks:write` stays blocked and disabled; a fresh valid token recovers
the same Routine with current authority and an unchanged policy fingerprint.
The development typing comparison also exposed six history-query bindings that
needed annotations under SQLAlchemy 2.1; all six now use the same explicit
sequence type as the existing `prior` annotations. Full-suite results are recorded below.

### Final combined-head cookbooks

**Status:** PASS

**Description:** Reran every Company cookbook after merging Heartbeat recovery,
using the Python 3.12 development environment and real PostgreSQL durable queue.
No live models or outbound messages were used.

**Result:** All 12 executions passed:

| File | Modes |
| --- | --- |
| `cookbook/05_agent_os/30_company/01_manage_products.py` | SQLite |
| `cookbook/05_agent_os/30_company/02_manage_projects.py` | SQLite |
| `cookbook/05_agent_os/30_company/03_manage_tasks.py` | SQLite |
| `cookbook/05_agent_os/30_company/04_manage_playbook.py` | SQLite |
| `cookbook/05_agent_os/30_company/05_product_manager.py` | Offline |
| `cookbook/05_agent_os/30_company/06_execute_tasks.py` | Manual SQLite/PostgreSQL; automatic SQLite/PostgreSQL, including authorized Project completion |
| `cookbook/05_agent_os/30_company/07_cascading_archive.py` | SQLite/PostgreSQL |
| `cookbook/05_agent_os/30_company/07_heartbeat.py` | SQLite |

### Final combined-head release probes

**Status:** MIXED — original incompatibilities and remaining assertions are explicit.

**Description:** The original Python scripts were byte-identical copies of the
release probes. Reran them and the documented compatibility copies against this
worktree with AGNO_DEBUG/AGNO_MONITOR unset, PostgreSQL `ai_claude` on port 5532,
HTTP capture on 8161 and performance on 8110. Compatibility copies retain their
authority assertions while supplying mandatory expiry, explicit Intake proposals
and observed hashes, the current cron argument and current fresh-schema checks.

**Result:**

| Probe | Original | Current API compatibility copy |
| --- | --- | --- |
| A identity/scopes | 222/225 | 223/225; two expectations omit the executor run scope and correctly receive 403 |
| C isolation | 54/55 | 54/55; existing subject-less shared read returns 200 |
| D registration/disabled | Stops at retired migration imports; 12 pass, two unsupported/signature/connection failures | 15/16; Mongo target deliberately points to unavailable port 1 |
| D main disabled | No Company routes or tables | Same |
| D2 legacy migration | Retired `v3_1_4`/`v3_1_5` import failure | Obsolete, not counted as a pass |
| E concurrency | Old Intake call lacks proposal argument | 14/14, including all four adapters and 20 repetitions per race |
| E2 async concurrency | Old Intake call lacks proposal argument | 6/6, async SQLite/PostgreSQL |
| F authority | Old cron argument and now-forbidden plain Routine proposal | 20/22; two payload-shape expectations exceed scheduler contract, no widened authority reproduced |
| F2 scheduler fence | Executor and Routine writes both denied; zero schedules | Same |
| G setup/fingerprint | Missing required expiry prevents setup of the policy | Nonblank setup refused; all three fingerprint stability comparisons true |
| Product Manager | GET 200 | GET 200 |

These are observed outcomes, not a claim that every original probe passes.
Baseline read/payload expectations remain outside the Automation change. The
required Company tests independently exercise forged payloads, current human
run permissions, executor-less Intake, concurrent ticks and real queue execution.


### Combined-head integration and validation gates

**Status:** PASS

**Description:** Complete Company, scheduler and lifecycle integration suites on
sync/async SQLite and PostgreSQL, plus the repository format and validate scripts.

**Result:** **771 integration tests passed**, with four optional MongoDB lifecycle
skips because AGNO_TEST_MONGO_URL was not set. Every requested SQLite/PostgreSQL
case executed. The extra 18 creation-recovery checks passed after the final
optional-payload typing correction. Clean Python 3.10 validation passed all
1,155 framework files and 21 CLI files; complete formatter and validator output
was read. The Python 3.12 comparison reports **34 identical baseline diagnostics
in 11 files** on the parent and final head, with zero introduced diagnostics.
Both original `prior` annotations and the six additional async history-query
annotations are present. Unrelated baseline formatter changes were inspected
and excluded before exact-tree validation.

Performance on the combined head again seeded 50 Products, 500 Projects, 5,000
Tasks and 200 wiki pages. Reads completed and all ten queued workflow Tasks
were independently confirmed In review. Live-model Intake recorded failure
because OPENAI_API_KEY was absent. The probe's server and unique schema were
cleaned up; no live-model success is claimed.

### Final main validation

**Status:** PASS after database fixture corrections

**Description:** Full database/OS/scheduler units plus Company tools, and the Company/scheduler/lifecycle/filesystem matrix on the published recovery fixes.

**Result:** The complete combined unit run had **6,391 passed, 8 optional/environment skips**, and five stale Mongo/Firestore migration-fixture failures. Their setup now explicitly calls upsert_run, matching the current persistence contract and SQLite equivalents; every assertion is retained and adapter behavior is unchanged. Both migration modules passed all 14 tests, then the **complete database unit suite passed 1,627 tests with one root-only skip**. All OS, scheduler and Company tool tests passed in the combined run; they are unchanged by the fixture correction. No unresolved unit failures remain.

Integrations: **676 passed, no skips**, including SQLite/PostgreSQL sync/async and MongoDB scheduler parity. Focused recovery/authorization: **159 passed**. All **10 cookbook invocations passed**. Format and exact-tree validate passed with full output read (mypy: 1,155 framework and 21 CLI files); diff whitespace checks passed. An earlier test-token scope omission and the creator-name-bucket recovery lookup were corrected before the final combined run. Optional dependencies changed in the shared environment, enabling the Firestore checks; this explains the changed totals and skips. No live model or outbound messaging calls.

---


### Final complete unit rerun after parent fixture corrections

**Status:** PASS

**Description:** Ran the complete `libs/agno/tests/unit/db`,
`libs/agno/tests/unit/os` and `libs/agno/tests/unit/scheduler` suites, plus Company
and SchedulerTools unit tests, on the final merged head. The replacement
Python 3.12 development environment was completed with missing adapter and
interface dependencies, including telebot.

**Result:** **6,537 passed, 5 conditional skips**, no failures. The
preceding full run had 6,532 passes and five Mongo/Firestore migration-fixture
failures; all five reproduced on unchanged Heartbeat. Heartbeat then published
fixture corrections in `2d4acd89a9`, integrated with normal merge `f468e3db62`.
All 14 affected cases passed independently before this complete successful
rerun. The correction changes test setup only, so the 771 passing integrations,
12 passing cookbook executions and recorded probes cover the same final runtime.
Skips are the root-only filesystem case, three live-provider cases without
OPENAI_API_KEY and the optional asyncpg configuration case. No history rewrite
followed the early rebase publication. Final format and clean validation passed;
all output was read and the exact source tree was checked after excluding
unrelated baseline formatter changes.


### Automation review fixes and timestamp compare-and-set — October 16, 2026

**Status:** PASS

**Description:** Automatic completion rechecks the Routine's Product and Refresh
binding after server checks. Scheduler startup reconciles the managed automation
row with Company configuration, before polling. Automatic Task and Project
transitions now compare the observed `updated_at` in SQL, preserving the existing
status predicates, terminal-Task gate and Product-locked budget. Full-row and
Task-list snapshots are removed. Dispatch carries only id, status and timestamp.

**Result:** The initial 20 review regression cases reproduced both defects on all
four SQL adapters, then passed with the fixes. The final timestamp design removes
the second completion-page rendering, retaining the Product/template race checks
at the server-check boundary. All original refusal, revocation and exhausted-budget
assertions remain. The timestamp audit covers edits, transitions, direct/cascading
archive and restore, run reservation, and error/success completion. Every path
already stamps epoch seconds. Explicit None matches SQL NULL; omitting the
observation is allowed only for manual transitions. Same-second writes remain
indistinguishable, with the existing status predicate still enforced.

Cookbook rerun: **12/12 PASS**, no live model calls:

- `01_manage_products.py`, `02_manage_projects.py`, `03_manage_tasks.py`:
  Product/Project/Task lifecycle and archive behavior.
- `04_manage_playbook.py`, `05_product_manager.py`: versioned wiki and restricted
  Product Manager wiring.
- `06_execute_tasks.py`: manual and automatic modes on SQLite and PostgreSQL;
  real durable queue execution, one Task attempt and human-review result.
- `07_cascading_archive.py`: SQLite and PostgreSQL cascade/refusal/restore/counts.
- `07_heartbeat.py`: offline Routine, Source, Intake and Refresh behavior.

Final validation on the timestamp-CAS tree:

- **6,570 passed, 5 conditional skips**: full `tests/unit/db`, `tests/unit/os`
  and `tests/unit/scheduler`, plus Company and SchedulerTools units.
- **733 passed, no skips**: all Company integration files on sync/async SQLite
  and PostgreSQL, plus SQLite scheduler, schedule lifecycle (PostgreSQL/MongoDB
  enabled) and schedule-owner recheck suites.
- **315 focused Company/scheduler units passed**, included in the full run.
- `./scripts/format.sh` and clean `./scripts/validate.sh` passed; complete output
  was read. Clean mypy checked 1,155 framework and 21 CLI files with no errors.
  Tests, cookbooks and formatting used the Python 3.12 development environment;
  clean validation used Python 3.10. Python 3.12 validation still reports the
  same 34 baseline diagnostics in 11 files as the recorded parent and pre-change
  runs, with no new diagnostics. Unrelated formatter edits were inspected and
  excluded before exact-tree validation. Whitespace checks passed.

An intermediate broad unit run with the superseded completion re-render failed
two synthetic managed-role cases. The final full rerun above passes both, with
permission-refusal assertions intact. The external release scripts were not
rerun in this follow-up; their earlier outcomes remain recorded above.
## Optional Routines and discovered website Sources — October 16, 2026

### 08_custom_routines.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/08_custom_routines.py` using
the development Python environment. Declared a Product with custom instructions,
no template and no initial Sources. Saved a website through CompanyTools with
injected agent/run identity, verified identical additions reused one Source,
and archived it through the human HTTP route.

**Result:** Passed without a model call, website request or outbound delivery.
The stored template is null; Product, template and auto_accept metadata keys and
the explicit Product message format are unchanged.

---

### Complete Company cookbook regression

**Status:** PASS

**Description:** Executed `01_manage_products.py`, `02_manage_projects.py`,
`03_manage_tasks.py`, `04_manage_playbook.py`, `05_product_manager.py`,
`06_execute_tasks.py`, `07_cascading_archive.py`, `07_heartbeat.py`, and
`08_custom_routines.py`. Also ran `06_execute_tasks.py` with
`COMPANY_DB=postgres` and `07_cascading_archive.py --postgres`.

**Result:** All 11 invocations passed. No live model/provider calls or outbound
messages. The PostgreSQL archive example exercised sync and async paths.

---

### Routine, Source, Summary and isolation regression suites

**Status:** PASS

**Description:** Ran Company and scheduler integrations with SQLite, async
SQLite, PostgreSQL and async PostgreSQL, including real durable queue execution,
lifecycle parity, scheduler ownership and filesystem transactions. The offline
search model discovers a page, saves and reads it through CompanyTools, then
proposes one evidence-backed Task over three schedule runs. Custom instruction
and executor edits take effect on the next run; unauthorized targets are refused.
Concurrent Source additions share an id, preserve first-discovery provenance and
refuse conflicting configuration or an archived reference. Agent tools still
cannot accept or complete Tasks. Summary acknowledgment tests cover retry,
cancellation, completion and archive. Missing-subject scoped tokens are rejected
on Company reads under isolation using the existing identity guard.

**Result:** Final integration rerun: 708 passed, no skips. Final focused
router/tool/heartbeat parity regressions: 205 passed. Scheduler execution
examples also passed all eight sync/async SQLite/PostgreSQL cases. An initial
Summary fixture tried an invalid In progress-to-Ready transition; it now uses
the existing Backlog-to-Ready retry path. The new optional Source configuration
uses the established nullable Company argument convention after schema tests
caught a non-nullable schema. No unresolved focused or integration failures.

`./scripts/format.sh` and `./scripts/validate.sh` passed, with their complete
outputs read. Exact-tree validation passed after excluding four unrelated
formatter-only changes. Mypy checked 1,155 framework and 21 CLI files. Tests and
cookbooks used development Python 3.12; validation used clean Python 3.10.
`git diff --check` passed. Source provenance uses the existing `config.metadata`
JSON object, with no table or column changes.


### Complete database, AgentOS, scheduler and Company tool unit suites

**Status:** PASS

**Description:** Reran the complete `libs/agno/tests/unit/db`,
`libs/agno/tests/unit/os`, `libs/agno/tests/unit/scheduler`, and
`libs/agno/tests/unit/tools/test_company.py` suites on the final implementation.

**Result:** 6,436 passed, five conditional skips, no failures. Skips were one
root-only check, three live-model credential checks and one optional asyncpg
check. The earlier four new Source-schema failures are resolved. Implementation
commit `dfaf0a59d7` was pushed for review while this final run completed; this
record follows as a normal commit without rewriting history.


### PR 6 integration with final Heartbeat head (17d5939068)

**Status:** PASS

**Description:** Integrated the final Heartbeat head as a normal merge after the timestamp compare-and-set changes. Preserved custom Routines, editable instructions and scheduler fields, discovered website Sources, and automatic acceptance. Added regression coverage for null-template completion denial, instruction edits preserving fingerprints and spent budgets, discovered website evidence, and policy reauthorization on executor edits.

**Result:** 773 Company/scheduler integration tests passed without skips across SQLite/PostgreSQL sync/async and configured scheduler backends. 354 Company/scheduler unit tests passed. All 13 cookbook executions passed, including `08_custom_routines.py`, Task execution in SQLite/PostgreSQL manual/automatic modes, and PostgreSQL cascading archives. The focused merge regressions separately passed all 16 cases.

`./scripts/format.sh` and clean-environment `./scripts/validate.sh` passed; complete outputs were read (1,155 framework and 21 CLI files checked by mypy). Development Python 3.12 validation retains the same 34 baseline diagnostics, with zero introduced. The previous complete database/OS unit run remains historical; this merge reran the Company/scheduler suites. Earlier external release probes were not rerun. Tests and cookbooks used offline execution.
