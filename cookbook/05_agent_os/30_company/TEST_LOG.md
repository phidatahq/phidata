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
