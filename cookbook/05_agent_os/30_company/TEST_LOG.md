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
