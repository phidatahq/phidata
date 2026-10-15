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
