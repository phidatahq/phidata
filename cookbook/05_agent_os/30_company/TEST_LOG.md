# Company validation record — Task ownership and recovery

**Date:** October 16, 2026

**Branch:** `codex/company-task-recovery`

**Base:** `2dec52a7e7bf202c3913b1d442220227525ce73a`

**Validated tree:** the implementation, tests, README and examples in the commit
containing this record. The implementation was published for parallel review as
`51b03980c696c296a1780b31dad20001c2c1b561`; the final follow-up changes this validation
record only. The PR reports the final full commit SHA. This single record
supersedes the historical entries; Git retains their previous versions.

## Integration validation

**Status:** PASS — 1,744 distinct integration cases, including all 50 new
regressions. No skips or failures.

The four follow-up fixes preserve remote Running attempts, restore disabled-owner
checks for new work, implement MongoDB schedule-history retention, and provide a
native synchronous attention reader. `test_company_replica_offboarding.py` adds
50 regression cases:

- Eight real two-process checkpoint cases across four SQL adapters and both
  isolation modes. The worker has executed a tool and persists Running; another
  process loses the ticket and recovers twice without cancellation or replay.
  The worker then completes and the Task receives its completed result.
- Twenty-four disabled-owner cases across Agent, Team and Workflow, four SQL
  adapters and both isolation modes. A lost completed result still recovers;
  new manual and automatic work is refused; the automatic refusal records one
  failure and returns the Task to Backlog; an authorized collaborator can cancel
  existing work after its owner is disabled.
- Eight fail-closed directory checks across four SQL adapters and both isolation
  modes. Directory errors refuse new Company work with HTTP 503.
- Eight real MongoDB retention cases: both Mongo adapters paired with all four
  SQL Company stores. Refresh removes old completed automation history, retains
  recent/incomplete/other-schedule rows, and continues to completion proposals.
- Two synchronous attention cases inside an event loop, on SQLite and PostgreSQL,
  with empty and paginated histories, product filtering and stale-failure removal.

The prior actor/owner, authorization, recovery-error and failure-streak matrices
remain in the complete integration selection.

**Result:** All four disjoint partitions passed 436 cases each on implementation
`51b03980c696c296a1780b31dad20001c2c1b561` (259.39, 262.49, 274.26 and 279.01
seconds). Both PostgreSQL and MongoDB were explicitly enabled. A separate clean
run of all 50 new regression cases passed in 73.98 seconds. These final runs
supersede the earlier development runs and prior-head validation.

The full Company integration tree was collected once and partitioned into four
disjoint runs. It includes every `test_company_*.py`, Product/Project/Task and
schedule lifecycle parity suites, and the SQLite Product/Project/Task suites.
The four Company adapters are sync SQLite, async SQLite, sync PostgreSQL and
async PostgreSQL. PostgreSQL used the local service on port 5532; MongoDB used port 27017.

The new ownership and recovery suite covers:

- Alice's first attempt and Bob's revision on the same Alice-owned session,
  with `started_by` retaining the human actor. Agent, Team and Workflow routes
  run in both isolation modes, with token scopes and managed roles.
- Missing executor run permission returns 403. Automatic pickup retains the
  accepting human as actor while keeping the Task owner as the run user.
- Legacy starter-owned reservations and queue tickets recover with their
  recorded identity. A subsequent attempt adopts the idle session only after
  matching its original reservation and run. Unrelated session owners return 404.
- Paused Routines and revoked policies do not prevent existing-attempt cleanup
  or completed-result projection. Recovery is fenced against enqueueing.
- Ticketless Pending attempts are cancelled. Running attempts remain observable
  until durable completion or explicit cancellation; registry absence alone is
  not authoritative liveness evidence. Missing ticket-and-run reservations receive a
  cancelled Task result and can start a new numbered attempt.
- Concurrent worker projection and recovery settle once. Competing completed,
  failed and cancelled terminal results preserve exactly one winner.
- Repeated identical dispatch errors retain one failed history row with a
  count, including failure immediately after automatic acceptance. A new reason
  or Task move resets the count; attention drops stale failures.
- Refresh applies configured 7-day and default 30-day automation retention,
  preserving recent and unfinished rows, through the actual Company tool.

Reproduce the integration selection with the development Python and
`PYTHONPATH=libs/agno`:

```bash
.venv/bin/python -m pytest \
  libs/agno/tests/integration/db/test_company_*.py \
  libs/agno/tests/integration/db/test_{products,projects,tasks,schedule}_lifecycle_parity.py \
  libs/agno/tests/integration/db/sqlite/test_{products,projects,tasks}.py \
  -q --disable-warnings --tb=short -o log_cli=false
```

Set `AGNO_TEST_POSTGRES_URL` and `AGNO_TEST_MONGO_URL` to the local services to
include optional schedule lifecycle and MongoDB cases. The Company PostgreSQL
fixtures already configure the local service.

## Unit validation

**Status:** PASS — 6,458 tests, 39 conditional skips, no failures.

**Description:** Reran the complete database, OS (including authorization),
scheduler and Company-tool suites on the review-fix implementation.

**Result:** All selected unit suites passed in 536.61 seconds. The command was:

```bash
.venv/bin/python -m pytest \
  libs/agno/tests/unit/db libs/agno/tests/unit/os \
  libs/agno/tests/unit/scheduler libs/agno/tests/unit/tools/test_company.py \
  -q --disable-warnings --tb=short -o log_cli=false
```

## Cookbook validation

**Status:** PASS — all 15 invocations on the review-fix implementation.

All paths below are relative to `cookbook/05_agent_os/30_company/`. Each example
was executed using the development Python with this worktree's framework on
`PYTHONPATH`. These use deterministic local components and make no model calls.

| Test | Modes | Description and result |
| --- | --- | --- |
| `01_manage_products.py` | SQLite | PASS: ownership filters, archive and restore assertions. |
| `02_manage_projects.py` | SQLite | PASS: collaborative Project lifecycle and ownership. |
| `03_manage_tasks.py` | SQLite | PASS: acceptance, frozen scope, transitions and restore. |
| `04_manage_playbook.py` | SQLite | PASS: sync/async wiki, version conflicts and decisions. |
| `05_product_manager.py` | SQLite | PASS: model resolution, bounded tools and MCP setup without inference. |
| `06_execute_tasks.py` | SQLite and PostgreSQL, manual and automatic | PASS in all four modes: durable execution, duplicate start, result and attention assertions. |
| `07_cascading_archive.py` | SQLite and `--postgres` | PASS in both modes: active-work refusal, cascading archive and exact restore. |
| `07_heartbeat.py` | SQLite | PASS: declarations, Source evidence, Routine persistence and duplicate-free intake. |
| `08_custom_routines.py` | SQLite | PASS: custom Routine and discovered website Source configuration. |
| `09_task_session_ownership.py` | SQLite and PostgreSQL | PASS in both modes: Alice/Bob attempts share one Alice-owned session and retain separate actor attribution. |

For execution examples, `COMPANY_DB=postgres` selects PostgreSQL session and
Company storage; their durable queue uses PostgreSQL in both modes.
`COMPANY_AUTOMATION=1` selects automatic execution in `06_execute_tasks.py`.

## Format, validation and scope

**Status:** PASS

Full repository `./scripts/format.sh` and `./scripts/validate.sh` run with the clean
Python 3.10 validation environment. The full formatter also normalizes existing
import ordering and wrapping in twelve unrelated files; those edits are mechanical.
No executor enum, Source type or sandbox acceptance behavior is changed here.

**Result:** Full Ruff formatting/import sorting and lint passed. Mypy passed for
1,182 framework files and 21 CLI files. The cookbook pattern check passed all 13
checked quickstart files with no violations. `git diff --check` passed.

These are local tests, not CI, independent review or hosted deployment evidence.
No paid model calls or real outbound notification deliveries were exercised.


### 09_sandboxed_engineers.py

**Status:** PASS

**Description:** Ran `PYTHONPATH=libs/agno .venv/bin/python cookbook/05_agent_os/30_company/09_sandboxed_engineers.py --config-only` on October 16, 2026. Both ClaudeAgent and CodexAgent accept the repository, isolated Docker network, explicit checkpoint store, workspace size and execution timeout configuration.

**Result:** Configuration smoke passed without model calls. The credential-free sandbox fixture separately exercised real public GitHub checkout, Task pin projection, container replacement, attempt-two session reuse, concurrent admission and acceptance on sync/async SQLite and PostgreSQL Company stores. The Claude and Codex model turns were not run.

---

### Sandboxed Company executor regression checks

**Status:** PASS

**Description:** October 16, 2026: all 1,344 Company integration cases passed across synchronous and asynchronous SQLite and PostgreSQL (eight conditional Mongo cases skipped). The affected unit suites passed 3,417 tests (35 conditional skips). All 12 Company Docker fixture cases passed, including cancellation during submission, and all 25 existing AgentOS sandbox cases passed, including the opt-in public-repository case. The Docker fixture used PostgreSQL, Redis and `agno-sandbox:pr71-repository`; no Claude or Codex model turn was invoked.

**Result:** Full format and validation scripts passed; validation used the clean Python 3.10 environment. These are local checks, not CI or independent review. PR 6.6 integration remains pending: its recovery completion must share the checkout projection before recovered sandbox completions can be claimed as covered.

---

### PR 7.2 review fixes — retry pins and live execution admission

**Status:** PASS

**Description:** Failed or cancelled first attempts no longer prevent a later successful attempt from storing the checkout pin. Admission reads live queue tickets using their recorded executor, including after Backlog return, reassignment, archival, or a newer Task reservation; a retained run still blocks when its ticket is missing. Added four-adapter regressions for both blockers and for authorization before admission. External agents are refused as team members, Windows/UNC local git paths remain valid, legacy Source references can be edited without replacement, and an explicit read-token Source requires `GITHUB_READ_TOKEN` in the sandbox environment.

**Result:** 1,751 affected unit tests passed (35 conditional skips), all 12 Company Docker cases passed, and the focused review suite passed 170 tests. The broad Company integration run passed 1,368 cases with eight conditional Mongo skips; its 16 failures exposed executor validation occurring after endpoint construction in the permission cleanup. That order was corrected, and all 16 failed cases passed on rerun, giving 1,384 distinct passing Company cases. A further final-source focused route run passed all 88 cases. Full format, clean Python 3.10 validation and whitespace checks passed. No paid model turns were run. PR 6.6 recovery integration remains deferred until it merges.

---

### PR 7.2 second review — admission, retries and migration

**Status:** PASS

**Description:** Settled historical attempts are excluded before resolving retired run stores. Live-ticket enumeration propagates failures for admission, includes untagged jobs claimed by named deployments, and uses the existing quiet-contention response for automatic pickup. Checkout validation errors can retry after their cause is repaired. Acceptance refuses a repository or branch incompatible with an established checkout. Migration diagnostics identify Task upgrades, adapter subclasses migrate correctly, and terminal rows retain their status without invalid transitions.

**Result:** All 96 focused regressions passed across sync/async SQLite and PostgreSQL. The affected unit suite passed 1,751 tests (35 conditional skips); all 12 Company Docker cases and all 183 queue-store parity cases passed. All 1,428 Company integration cases passed, with eight conditional Mongo skips. Full format, clean Python 3.10 validation and whitespace checks passed. No paid model turns were run. PR 6.6 dispatch and recovery functions remain unchanged; recovery pin integration is deferred until that PR merges.

---

### PR 7.2 rebase and overlapping deployment admission

**Status:** PASS

**Description:** Rebased onto the latest PR 6.6 head, `f238e6892a9cfd634363fd0c41dfcb6c668fee3f`. Preserved its authenticated internal transport and passed the trusted checkout metadata through that application path. Admission uses a common advisory lock because named workers can claim untagged jobs. A deterministic two-application regression reproduced two accepted starts in all eight adapter/ordering cases before the fix; all eight now admit one start and refuse the other.

**Result:** All 104 focused regressions passed across sync/async SQLite and PostgreSQL. The affected unit suite passed 1,751 tests (35 conditional skips); all 12 Docker and 183 queue-store parity cases passed. Cookbook configuration smoke, full format, clean Python 3.10 validation and whitespace checks passed. The initial combined run passed 1,840 cases and exposed four recovery-test failures caused by this module leaving Redis process defaults attached to a closed test event loop. The fixture now restores those defaults; all 24 ordered concurrent-start/recovery cases pass. A clean 1,844-case combined rerun is in progress at publication; its final results are recorded in the PR. No paid model calls. Recovery checkout projection remains deferred until PR 6.6 merges.

---

### PR 7.2 recovery checkout integration

**Status:** PASS

**Description:** Merged main after PR 6.6 landed, using normal merge commit `4554646f1e`. Recovered completed runs now use the same checkout projection as worker completion. The first successful recovery stores the pin, later attempts verify it, missing or changed pins fail the attempt, and an unavailable sandbox executor leaves recovery retryable. The checkout and result use the existing guarded atomic completion write; a stale recovery cannot replace a settled winner.

**Result:** All 20 recovery regressions passed across sync/async SQLite and PostgreSQL. The complete Company/lifecycle matrix passed 1,864 cases with PostgreSQL and MongoDB enabled and no skips. The affected unit suite passed 1,751 tests (35 conditional skips); all 12 Docker and 183 queue-store parity cases passed. Cookbook configuration smoke, full format, clean Python 3.10 validation and whitespace checks passed. No paid model calls. These are local results; CI and independent review remain separate.

---

### PR 7.2 pinned Task acceptance consistency

**Status:** PASS

**Description:** Sync and async acceptance now reject a pinned Task's reassignment to a non-sandboxed agent, team or workflow with HTTP 409. Unpinned Tasks retain their existing behavior. The four-adapter regression covers refusal without mutation and successful session/pin reuse and recovery after selecting a compatible sandboxed executor. All 12 pinned cases failed before the fix; all 24 pinned/unpinned cases pass afterward.

**Result:** All 148 focused sandbox/checkout tests, 1,751 affected unit tests (35 conditional skips), and 12 Docker cases passed. The broad Company/lifecycle run passed 1,886 cases and exposed two async concurrency fixtures pausing at the new preliminary validation read rather than the intended SQL transition read. The fixture now pauses within the transition transaction; the complete 40-case Task lifecycle suite passed on rerun, yielding 1,888 distinct passing integration cases. Full format, clean Python 3.10 validation, cookbook configuration smoke and whitespace checks passed. No paid model calls. Recovery and queue admission production code are unchanged.

---

### PR 8 — checkpoint outputs and bounded attachments (2026-10-16)

**Status:** PASS

**Description:** Completed sandbox runs produce durable checkpoint patches before
review, including empty and lossless binary patches, untracked files and patches
larger than the ordinary filesystem's 1 MB default. Verified pin and size
failures, missing-attempt 404s, tasks:read authorization, failed-projection retries,
non-UTF-8 patch application/download, nested repository/gitlink refusal,
interrupted-projection recovery, attachment count/byte limits and unchanged
ordinary-executor results. Sandbox instructions require uncommitted changes.

**Stack:** Integrated PR 7.2 head `be1fc9ac3ce7a174215a956b492ea81f3f052c2d`
with a normal merge. Recovery resolves the recorded run's executor and retains
its checkout pin, then uses the shared patch projection before review. Missing
sandbox executors defer recovery. Pinned Tasks refuse non-sandboxed reassignment.
Parent recovery tests use real local-repository checkpoints for completed runs.
Multipart wiki attachments retain the ownership-aware internal run transport.

**Result:** All **386 focused unit/integration tests**, **84 execution-recovery
tests**, and **12 Docker/Redis/PostgreSQL Company fixture cases passed**, with no
failures or skips. SQL coverage includes synchronous and asynchronous SQLite
and PostgreSQL; Docker coverage includes identical patch downloads after
container replacement. The local repository fixture separately verifies
nonempty replacement patches. Full format and clean Python 3.10 validation,
whitespace checks and the Claude/Codex cookbook configuration smoke passed.
Tests used the Python 3.12 development environment.

The earlier full database/AgentOS unit rerun passed 6,260 tests with 39 conditional
skips; that full suite was not repeated for this focused parent integration.
Earlier review fixes were published before their unit tests as requested. No
paid model turns, hosted-provider deployment or CI success is claimed here.

---

## PR 9: host publication and verified completion

### test_company_publication.py and test_github.py

**Status:** PASS

**Description:** 120 focused cases passed across SQLite, async SQLite, PostgreSQL and async PostgreSQL, plus JWT/managed-role routes and the existing GitHub toolkit suite. Real bare Git remotes cover first publication, crash recovery before and after PR creation, concurrency, revisions, exact merge ancestry, mismatched and closed PRs, required check runs, optimistic result fencing and sync/async entry points. GitHub calls replay checked-in API response shapes. Token assertions cover Git argv/config, Task records, persisted run rows, sandbox environment, schedule payloads and exception logs.

**Result:** All focused cases passed. Format and clean Python 3.10 validation passed. The wider suites ran after PR creation; see final validation below.

---

### 09_sandboxed_engineers.py --config-only

**Status:** PASS

**Description:** Both `--executor codex` and `--executor claude` configurations initialized successfully. Publication is gated behind `COMPANY_PUBLISH=1` and requires an explicitly selected repository and host write token.

**Result:** Configuration checks passed. No live model calls or actual GitHub publication were run.

---

### Publication authorization and parent compatibility follow-up

**Status:** PASS

**Description:** All 11 publication route/authorization tests pass, including four added cases for current managed accepting identity and permission to enable automatic publication. The wider sweep identified two legacy policy-fingerprint expectations and four candidate-paging expectations that needed the new false-by-default permission and In review reconciliation state reflected. All six corrected cases pass across their selected adapters/isolation modes.

**Result:** Follow-up assertions pass; production code is unchanged from the first PR publication. The wider sweeps are complete; see final validation below.

---

### Selected-attempt policy checks

**Status:** PASS

**Description:** Four SQLite/PostgreSQL sync/async cases verify that registered publication checks inspect the explicitly requested attempt's stored result. A check that approves attempt 1 refuses latest attempt 2 and permits an explicit publication of attempt 1.

**Result:** All four cases passed. This corrects the check input for older-attempt publication; GitHub check runs continue to target the exact generated head.

---


### PR 9 final validation

**Status:** PASS

**Description:** The final publication, sandbox-acceptance, authorization and GitHub suite passed all 151 cases. This includes the selected-attempt check correction, captured/default/SDK logger redaction, and checks against the actual sandbox environment including inherited SDK credentials. Both cookbook configuration modes passed without model calls.

**Result:** The broader unit sweep initially reported 12,322 passed, three failed and 55 conditional skips. Two legacy fingerprint assertions were updated for the false-by-default publication permission; an unrelated AgentCore constructor test needed the unavailable host AWS profile unset. All three affected files passed 103 cases on rerun with dummy AWS credentials. Including the four additional authorization cases and one captured-logger regression, 12,330 distinct unit cases passed across the sweep and follow-ups; 55 conditional skips remain.

The broader Company/lifecycle integration sweep initially reported 1,592 passed, four failed and 16 skips. All four paging expectations were updated to include In review and passed on rerun. The four new selected-attempt cases and four initially skipped PostgreSQL scheduler cases also passed. Final distinct integration coverage is 1,604 passes, with only 12 optional MongoDB cases skipped; no selected SQLite/PostgreSQL case remains failing or skipped.

Full format and clean Python 3.10 validation passed (1,187 framework and 21 CLI source files). GitHub lint/triage checks passed on the earlier published head; final hosted status remains separate from local validation. No paid-model calls or actual GitHub repository publication were performed. The PR was opened before the wider sweeps, and subsequent changes preserve its history with normal commits.

---

### PR 9 review corrections

**Status:** PASS (focused checks); wider reruns pending.

**Description:** Rebased onto PR 8 `52430cfe5c`. All 179 focused publication, authorization, sandbox and GitHub cases passed. New regressions cover registered-check gating without pre-push GitHub CI, unknown policy rejection, Refresh continuation after reconciliation failure, case-insensitive repository identity, merged-PR adoption after failed persistence, refusal of closed/different-head PRs, cached negative ancestry with transient-error retries, and consistent lock contention across all four SQLite/PostgreSQL adapters. The automatic-publication fixture now activates its Project before requiring `project_active`.

**Result:** Both Claude and Codex cookbook configuration modes passed without model calls. Full format and clean Python 3.10 validation passed. The review update is pushed before wider Company/lifecycle integration and DB/AgentOS/scheduler/tools/sandbox/context unit reruns finish, so review can proceed in parallel. No live publication or paid-model execution was performed.

---

### PR 9 review corrections — full regression results

**Status:** PASS

**Description:** The implementation was pushed at `390e2efa29` before the broader suites started, allowing review in parallel. The full DB/AgentOS/scheduler/tools/sandbox/context unit selection passed **12,330 tests**, with 55 conditional skips. The Company and lifecycle integration selection passed **1,700 tests**, with 12 optional MongoDB skips. All selected SQLite/PostgreSQL cases passed, including both sync and async adapters.

**Result:** No further code changes were needed after the review push. The focused 179-case suite, both cookbook configuration modes, full format and clean Python 3.10 validation also passed. This final update records results only; the code remains based on PR 8 `52430cfe5cc95db8890abb44abb4ab3c559fead4`. No live-model calls or actual GitHub publication were performed.

---

### PR 9 parent synchronization — ownership and recovery

**Status:** PASS (focused validation); wider suites pending.

**Description:** Integrated PR 8 `d444dc13a58016e99df67f4a74e7b2d34fee56d4` with a normal merge. The tick preserves In review publication/reconciliation without requiring an executor or queue ticket, while retaining the parent's independent recovery of reserved execution. The existing automatic-publication regression now asserts this separation with a queue present.

**Result:** All 179 focused publication, authorization, sandbox and GitHub cases passed across SQLite/PostgreSQL sync/async adapters. Both sandbox cookbook configuration modes, full format and clean validation passed (1,188 framework and 21 CLI source files). Broader ownership/recovery, authorization and lifecycle suites run after the push.

---

### PR 9 parent synchronization — wider validation

**Status:** PASS

**Description:** The normal merge of PR 8 `d444dc13a58016e99df67f4a74e7b2d34fee56d4` was pushed at `e0f4f820f4` before broader suites ran. The relevant database, Company routes/tools, scheduler and authorization unit selection passed **2,154 tests**, with 35 conditional skips. Execution, task identity recovery, actor/owner parity, replica offboarding, sandbox admission, patches, retention and task/schedule lifecycle integration suites passed **1,369 tests**, with 12 optional MongoDB skips.

**Result:** No failures or further code changes were needed after the merge push. The 179 focused tests, both sandbox cookbook configuration modes and full format/clean validation also passed. PR 8 remains open, so PR 9 retains its stacked base.

---

### PR 9 parent synchronization — recovered checkout safeguards

**Status:** PASS

**Description:** Normally merged PR 8 `f736b8c880696c59f625ccb9aef1ab7e24182336` at `c9301fc294eca1401137d365e4eda731d701351a`. The parent preserves pinned sandbox checkouts during recovery and requires sandboxed executors for pinned Tasks. The merge was conflict-free.

**Result:** All 179 focused publication/authorization/GitHub tests and full format/clean validation passed before pushing. Relevant broader suites ran after the push: 1,698 database/Company unit tests passed (35 conditional skips), and 339 sandbox admission, patch, Task lifecycle and identity/recovery integration tests passed with no skips. No failures or additional code changes were needed. PR 8 remains open and PR 9 retains its stacked base.

---
