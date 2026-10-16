# Company validation record — Task ownership and recovery

**Date:** October 16, 2026

**Branch:** `codex/company-task-recovery`

**Base:** `2dec52a7e7bf202c3913b1d442220227525ce73a`

**Validated tree:** the implementation, tests, README and examples in the commit
containing this record. The PR reports its full commit SHA. This single record
supersedes the historical entries; Git retains their previous versions.

## Integration validation

**Status:** PASS — all 128 review-fix regression cases; wider rerun in progress.

The review fixes separate actor authorization from session ownership for start
and cancel, persist executor defaults for unowned Tasks, and return controlled
409/503 recovery errors. The new `test_company_actor_owner_parity.py` matrix has
128 cases across all four SQL adapters and both isolation modes. It includes
Agent, Team and Workflow execution, token and managed-role authorization,
unauthorized cancellation without ticket mutation, automatic pickup, retained
default identity after configuration changes, and ordinary scheduler owner checks.
The 32 supplied offline review probes also passed.

The previous head `09b7d735b7` passed 1,554 distinct integration cases with 12
optional MongoDB skips. That result is superseded by the wider rerun in progress
for these fixes; it is not claimed as validation of the updated source.

The full Company integration tree was collected once and partitioned into four
disjoint runs. It includes every `test_company_*.py`, Product/Project/Task and
schedule lifecycle parity suites, and the SQLite Product/Project/Task suites.
The four Company adapters are sync SQLite, async SQLite, sync PostgreSQL and
async PostgreSQL. PostgreSQL used the local service on port 5532.

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
- Ticketless Pending and untracked Running attempts are cancelled. Tracked
  Running attempts are observed. Missing ticket-and-run reservations receive a
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

Set `AGNO_TEST_POSTGRES_URL` to the local PostgreSQL URL for the separate schedule
lifecycle suite. The Company PostgreSQL fixtures already configure that service.

## Unit validation

**Status:** Full database, OS, scheduler and Company-tool rerun in progress.

The prior head passed 1,966 affected unit tests with 35 conditional skips. The
updated middleware is being checked with the broader OS authorization suites as
well. The current command is:

```bash
.venv/bin/python -m pytest \
  libs/agno/tests/unit/db libs/agno/tests/unit/os \
  libs/agno/tests/unit/scheduler libs/agno/tests/unit/tools/test_company.py \
  -q --disable-warnings --tb=short -o log_cli=false
```

## Cookbook validation

**Status:** Rerun pending for the review fixes. All 15 invocations below passed
on the previous head `09b7d735b7`.

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
