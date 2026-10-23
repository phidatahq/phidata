# Customer feedback cookbook test log

## 2026-10-23

### company_os.py — startup and live UI workflow

**Status:** PASS

**Description:** Tested GPT-6.1 Sol against synthetic Markdown customer feedback.
Connected the AgentOS UI, triggered the Routine, inspected generated Projects and
Tasks, selected Feedback Analyst, saved the executor, and changed a Task from
Backlog to To do. Company automation dispatched the accepted Task.

**Result:** The Task reached Reviewing with a saved product brief and regression
plan (13,560 characters). The other Task remained in Backlog. The result
explicitly distinguished proposed behavior from verified implementation. The
initial UI exercise used the development checkout with the Company Manager
routine lookup repair. The PR uses current main's existing manager support and
Product-scoped Source tool names; its separate scheduled execution check is
recorded below when complete.

---

### Source quality and authority checks

**Status:** PASS

**Description:** Live Sol runs covered first discovery, repeat discovery,
positive/resolved feedback, an empty folder, and an unavailable folder.

**Result:** Discovery identified both actionable themes; a repeat created no
extra work; quiet and empty inputs created no work; a missing folder produced
a failed Routine. Proposals retained evidence links and content hashes and
stayed in Backlog. Built-in managers were rejected as Task executors. Separate
source checks covered recursive discovery, paging over 127 files, sync/async
parity, changed evidence, path traversal and symlink confinement.

---

### Clean PR validation

**Status:** PASS

**Description:** Ran `./scripts/format.sh` and `./scripts/validate.sh` on current
main plus this cookbook, using Python 3.10 and the repository's development
extras in an isolated environment.

**Result:** Both scripts passed. Earlier broad validation on the development
checkout passed 1,091 integration tests (8 skipped), 222 unit tests, and the
follow-up affected integration selection passed 145 tests. These earlier
counts are development-checkout evidence, not an exact-PR test count.

---
