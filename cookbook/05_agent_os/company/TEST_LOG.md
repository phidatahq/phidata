# Company manual slice validation

## Ready pickup and review gates — 14 October 2026

**Status:** PASS for behavior checks; full validation remains blocked by seven inherited typing errors.

**Description:** The existing scheduler picks up newly accepted Ready Tasks through
its durable queue. Successful execution stops at In review. An eligible human may
accept Done or link an exact GitHub PR revision for read-only merge verification.

**Results:**
- Backend Company, queue, scheduler, configuration and authorization selection:
  **382 passed, 2 expected Manager-only skips**; two existing OpenAPI warnings.
- Disposable combined checkout with Manager head
  `01a202354a7e5f5bd7fd0b61f60dc0a7bb7b24d3`: **324 passed**; four existing OpenAPI
  warnings. Includes all platform specialists, ordinary Product Manager composition,
  automatic Ready pickup, inline/queued Manager delegation and queue wakeup checks.
  Compatibility uses public ManagerConfig and the current platform-admin requirement.
- Company suite with isolated installed dependencies: **64 passed, 2 expected
  Manager-only skips**; two existing OpenAPI warnings. Source loaded from this checkout.
- Covered concurrent ticks, restart reconstruction, partial dispatch recovery,
  cancellation, failed-run non-retry, worker changes, revoked authority, migration
  v5-to-v6, human-only PR linking, duplicate completion, stale review races, plain
  evidence URLs, changed SHA, bot/old merges, malformed responses and GitHub failures.
- Actual read-only GitHub verification against an already-merged public PR accepted
  its exact historical head and rejected a wrong SHA and using that old merge for
  a new review. Full Task completion uses mocked GitHub HTTP in local integration
  tests; no new live agent calls or actual human-merge workflow was performed.
- `with_agents.py` constructs the Company routes and worker configuration without
  starting lifespan or making model calls. Starting lifespan can dispatch existing work.
- `scripts/format.sh`: PASS (three unrelated formatter-only baseline edits restored).
  Ruff, cookbook pattern checks and agnoctl typing: PASS. `scripts/validate.sh`: FAIL
  with seven typing errors outside Company, exactly reproduced on the unchanged
  parent commit `ca295d99e9b6f41ca9e829397f8320a751e7b8f4`. No new typing errors.

**Limits:** GitHub.com only; its User account type is not proof of physical human
interaction or branch-protection enforcement. No automatic failed-run retry, per-Task
workspace provisioning, frontend work, new live model evaluation or multi-host proof.
Existing Ready Tasks need renewed acceptance after migration; old reviews need a new
review cycle before PR verification. Sequential GitHub checks can delay scheduler ticks
at scale; production-scale rate-limit and throughput behavior is not established.

---

## Completion checks — 14 October 2026

**Status:** PASS for local backend checks and the two-run live Codex pilot.

- Required `scripts/format.sh` and `scripts/validate.sh`: PASS. The previous 26 model
  typing failures were resolved in a separate prerequisite commit. Related Google
  and Anthropic model tests: **261 passed**, including caller-owned client lifecycle.
- Company, durable queue, scheduler, configuration and authorization selection:
  **353 passed, 1 expected Manager-only skip**, two existing OpenAPI warnings.
- Company combined with Manager PR #11036 at
  `bccd20c6535b1324f15ae5a0ae27d0e9216cdcdb`: **107 passed**, four existing OpenAPI
  warnings. Both inline and queued delegation include all three platform specialists
  plus Product Manager and retain the initiating human's Product access.
- Cancellation now interrupts executing agents as well as waiting queue entries.
  A durable cancellation intent prevents partial dispatch from restarting cancelled
  work, including after its worker is removed from a deployment. Active, queued
  and pre-dispatch cancellation regressions: **3 passed**.
- Existing cookbook database upgraded from v4 to v5 without dropping data. Repeating
  `manual.py` preserved the original single completed Task and derived Project counts.
- The prepared two-run operator script passed with a fixture SDK, including an actual
  disposable worktree, independent command checks, restart, revision and acceptance.
  Those edits were scripted fixtures; this is not live coding evidence. The Company
  suite is also wired into the existing PostgreSQL CI job; hosted Company tests passed.
- No frontend changes or Manager PR edits. Automatic per-Task workspace allocation
  and multi-replica deployment are not established by these tests.

### Live Codex operator pilot

**Status:** PASS — two live runs out of ten authorized, using the configured Codex account.

**Description:** At runtime source `9530220fc71c902df0dbe335c97cbfde4f9da78b`, created
a disposable repository/worktree and a dedicated PostgreSQL database. Company HTTP
routes dispatched a registered CodexAgent through the durable queue. Run one fixed
the README command. After AgentOS reconstruction, run two revised the CLI to accept
either a positional name or --name and added three unittest cases. Reported model:
`gpt-5.6-luna`. Both runs retained the same Company session and native Codex thread.

**Result:** Independent checks passed: three unit tests, documented command, both CLI
forms, rejection of conflicting inputs and unchanged guide checker. Duplicate dispatch
requests created no extra runs. Each result stopped at In review; explicit acceptance
by the fixture reviewer moved the Task to Done and derived Project completion. The
source repository remained clean. No push, merge or deployment occurred in the pilot.

AgentOS was reconstructed within one process; this does not prove host/crash recovery.
The fixture reviewer is not an actual human PR merge. Live Manager Team planning,
automatic Ready pickup and verified human-merge completion were not exercised.

---

The entries below retain earlier test history; their failures and counts are superseded
by the completion checks above.


Date: 2026-10-14. Model-free local validation; no paid provider calls.
Backend base: `00497422d4a386d93ab3b45c1a11faf42fcc932f`.
Frontend base: `3ea02209d` in the separate agno-os workstream.

### manual.py

**Status:** PASS

**Description:** Printed `agno.__file__` from the isolated Company checkout, then
created Website / Improve onboarding / Correct the setup guide and explicitly
accepted Ready, In progress, In review, and Done through the shared service.
Repeated with the same keys, and repeated again after the version-2 migration.

**Result:** Persisted Done, one accepted Task / one Done Task, zero in review;
no duplicate logical operations. Evidence is a demonstration acceptance statement,
not a claim that a real guide or PR was tested.

---

### libs/agno/tests/integration/company/test_manual.py

**Status:** PASS

**Description:** 18 PostgreSQL/model-free regressions: persistence, membership and
operation policy, filtered counts, replay after revocation, contextual task parents,
composite FK enforcement, optimistic concurrency, idempotent concurrent creates,
archive/create races, lifecycle graph/reopening, explicit review, comment attribution,
async transaction offloading, conditional routes/imports/discovery, startup with no
Company connections/DDL, schema checks, pagination/cursor scoping, HTTP envelopes,
forged mutation metadata, and resync.

**Result:** All 18 passed. Combined with existing configuration, scope/provider,
authorization object and resync suites: **155 passed**, 2 deprecation warnings.
No live model evaluation. Concurrent tests prove the exercised schedules, not all
possible database/deployment failure modes.

---

### PostgreSQL migration and restore

**Status:** PASS

**Description:** Explicit version 1 -> version 2 migration of populated pilot data;
repeated migration, then pg_dump/pg_restore into a clean UTF-8 PostgreSQL database.

**Result:** All eight tables and the key sequence matched, including IDs, versions,
review history, idempotency results, and evidence. Neither migration represents a
previously released Company schema. No production upgrade was attempted.

---

### Frontend and browser pilot (separate repository)

**Status:** PASS

**Description:** Existing frontend routes/sidebar integrate the production Company
renderer. Its local browser acceptance fixture used real JWT authentication and
PostgreSQL API calls; platform login was outside the fixture. Keyboard-created the
complete Website journey, attached an inert example evidence URL, accepted Done,
reloaded, filtered Projects, tested reader/nonmember access, a genuine 412 conflict,
and a 320px layout. Temporary API failure retained dated data and recovered.

**Result:** Tasks stayed within Project context. Navigation remained Products /
Projects. No horizontal overflow at 320px. Frontend validation/build passed; see the
separate frontend report for final test totals and screenshots.

---

### Required backend scripts

**Status:** FAIL (baseline validation gate)

**Description:** `./scripts/format.sh` passed. `./scripts/validate.sh` passed all
ruff, agnoctl mypy, and cookbook-pattern checks, but agno mypy reported 26 errors in
five unrelated model/compatibility files. The identical 26 errors reproduced from
an untouched archive of the pinned main commit using the same development venv.

**Result:** No Company typing errors; the full gate remains blocked by baseline
errors. Formatting-only changes to three unrelated files were discarded from the
initially clean worktree. Nothing pushed, published, merged, or deployed.


### Simpler creation and Task-to-Project association (14 October follow-up)

**Status:** PASS

**Description:** Minimal HTTP bodies create Products and Projects without explicit
owners or draft criteria. Ownership is resolved from verified identity and parent
records. A direct Task can join an open same-Product Project or return to the Product
without losing its identity. Regressions cover replay, stale edits, activity,
counts, cross-Product/closed-Project rejection, inherited ownership, review locks,
and replay after the reviewer loses the required role.

**Result:** 21 Company tests passed; expanded AgentOS selection **158 passed**, with
2 existing duplicate OpenAPI operation-ID warnings. Checkout import confirmed from
`/Users/ab/code/agno-worktrees/company-manual/libs/agno/agno/__init__.py`.
Formatting and ruff pass. The full typing gate still reports the identical 26
baseline errors in five unrelated model files. No schema migration, model call,
frontend change, push or manager PR change in this follow-up.

---

### Minimal Company records, execution and recurrence (14 October approved slice)

**Status:** PASS — model-free backend validation; live provider pilot pending.

**Description:** `libs/agno/tests/integration/company` exercises nullable direct-Task
stages, derived Project completion, five Project Task stages, archive/restore,
v2-to-v4 data preservation, identity, membership, idempotency and concurrent edits.
Execution tests use real PostgreSQL and AgentOS queue/scheduler components with a
deterministic model. They cover result persistence, revision/session reuse, restart,
partial dispatch recovery, concurrent duplicate submissions, no overlap, cancellation,
disabled owners, recurrence pause, missed intervals, prior results, grouping, generated
summaries and agent/human audit attribution. Tool schemas hide identity inputs.

**Result:** 33 Company checks passed, with the manager compatibility check skipped on
the independent backend branch. The combined Company/queue/scheduler/configuration/
authorization selection passed **351 tests**, one expected skip and two existing
duplicate OpenAPI operation-ID warnings. Codex adapter tests used a fixture SDK and
an explicit disposable Git worktree: native thread reuse and result linkage passed;
no real coding model or containment boundary was evaluated.

---

### Manager compatibility

**Status:** PASS

**Description:** Combined the Company changes with the current manager Team source
in a disposable checkout. Product Manager is an ordinary Agent with CompanyTools,
appended to the manager Team. The test uses the normal Team HTTP and durable queue
paths and verifies the initiating user's Product permissions through delegation.

**Result:** **105 tests passed** across Company and the manager's own suite, with four
existing OpenAPI warnings. The separate integration probe includes Platform Manager,
Platform Builder and Platform Engineer beside Product Manager. No manager source,
active manager worktree or manager PR was edited by this Company workstream.

---

### manual.py and app.py

**Status:** PASS

**Description:** Migrated a fresh UTF-8 PostgreSQL database to version 4. Ran
`cookbook/05_agent_os/company/manual.py` twice using the same request identities.

**Result:** One Product, Project and Task persisted; the Task was Done, the Project
derived completion, and rerunning did not duplicate work. Verified the backend
worktree import path. An initial local database-creation attempt used the cluster's
SQL_ASCII maintenance database through SQLAlchemy and failed; raw psycopg creation
of an explicit UTF-8 database resolved that fixture setup issue.

---

### with_agents.py

**Status:** PASS (construction; no provider execution)

**Description:** Loaded the runnable Company/queue/scheduler example with local
PostgreSQL and test JWT configuration. Product Manager uses an ordinary CompanyTools
toolkit. The example supports the manager feature and an explicitly configured Codex
workspace without changing CompanyConfig's public assembly.

**Result:** Configuration constructed successfully without model calls. Live coding
quality, automatic workspace allocation and multi-replica deployment remain untested.

---

### Final format and validation

**Status:** Format PASS; full validation FAIL on the inherited typing baseline.

**Result:** Full format, ruff, agnoctl typing and cookbook checks passed. Targeted
Company typing passed. Full framework typing reports the same 26 errors in five
unrelated model files as the untouched base, compared after normalizing checkout
paths. No Company errors were added. No push or PR submission was performed while
that gate remains red. No frontend changes were made in this slice.

---
