# Test log

## Manager package and default offloading, 2026-10-14

### basic_manager.py

**Status:** PASS

**Description:** Constructed the app after moving the manager into its own package.

**Result:** OS Manager and its two members are created with default offloading.
Manager resources stay excluded from the build registry. No model calls.

---

### manager_builds_agents.py

**Status:** PASS

**Description:** Constructed the app and published Budget Helper through the
builder's create tool against a temporary SQLite database.

**Result:** The model, calculator tools and workflow functions remain available
for building; manager components remain excluded. No model calls.

---

### manager_with_resources.py

**Status:** PASS

**Description:** Constructed the app with a workspace and learning, then wrote
and read `project.md` through the manager's notebook tools.

**Result:** Three members are configured, and the saved note is returned. No
live-model memory or source explanation was tested.

---

### manager_diagnostics.py

**Status:** PASS

**Description:** Ran the script with `OPENAI_API_KEY` unset and model calls blocked.

**Result:** Completed the report and reported the missing required key as FAIL.

---

### Manager offloading regression checks

**Status:** PASS

**Description:** Ran the manager, diagnostics and offloading unit suites. New
cases exercise delegation and each specialist directly, in sync and async mode,
with default offloading, explicit opt-out and custom ResultStore settings.

**Result:** 186 tests passed, including 24 new manager cases. Stored results can
be read beyond their previews; reads by another user or session are rejected.
Two existing duplicate OpenAPI operation-id warnings remain. Tests use SQLite
and scripted models; no live provider or PostgreSQL run was performed.

---

## Revised manager examples, 2026-10-14

Used `.venv/bin/python` with this checkout's `libs/agno` on `PYTHONPATH`.
Serving examples were loaded from a temporary working directory. Model calls
were blocked in the smoke check; no live conversations or servers were started.

### basic_manager.py

**Status:** PASS

**Description:** Constructed the OS and FastAPI app without an explicit registry.

**Result:** OS Manager has two members and uses the revised instructions. No
manager models, tools or components entered the build registry.

---

### manager_builds_agents.py

**Status:** PASS

**Description:** Constructed the app and called the builder's create tool directly
to publish Budget Helper with calculator tools.

**Result:** Publishing succeeded using the declared model and calculator. The
registry contains the three JSON/CSV functions and excludes manager components.
The README's live conversation and arithmetic response have not been tested.

---

### manager_with_resources.py

**Status:** PASS

**Description:** Constructed the app with three manager members, a notebook and
learning. Called the manager's notebook tools to write and read `project.md`.

**Result:** The saved note was returned. Learning is attached to the manager,
and manager resources remain excluded from the build registry. Cross-session
memory and source explanation through a live model have not been tested.

---

### manager_diagnostics.py

**Status:** PASS

**Description:** Executed with `OPENAI_API_KEY` unset and model calls blocked.

**Result:** Completed the report and correctly reported the missing required key
as FAIL. No registry setup or source workspace was needed.

---

### Manager and diagnostics unit tests

**Status:** PASS

**Description:** Ran `test_manager.py` and `test_diagnostics.py` against the revised
prompt, field placement and component exclusion message.

**Result:** 87 passed. Two existing duplicate OpenAPI operation-id warnings were
reported. Targeted Ruff formatting and lint checks also passed. These checks do
not establish live-model prompt quality.

---

## Diagnostics regression validation, 2026-10-14

### manager_diagnostics.py

**Status:** PASS

**Description:** Executed with the development environment against the updated
branch after pulling `ad76cf015a`. Deliberately unset `OPENAI_API_KEY`; no model
calls were made.

**Result:** SQL connectivity passed without provisioning session tables. The
overall report correctly returned FAIL for the missing required environment
variable, and WARN for disabled authorization. Manager wiring and sync/async
session persistence also passed a separate scripted-model smoke check.

### Diagnostics regression tests

**Status:** PASS

**Description:** Covered broken and empty SQL databases with sync and async
adapters, schedules beyond page one, incomplete scans, later-page errors, and
real in-process MCP initialization at default, custom and host-root endpoints.
Also checked a proxy path prefix.

**Result:** All 16 new cases passed; 11 fail against the pre-fix diagnostics
implementation. The combined manager, diagnostics, scheduler and queue suites
passed 369 tests. No external model calls or live PostgreSQL checks were made.

---

Executed 2026-10-14 with `/Users/ab/code/agno/.venv/bin/python` and this branch's `libs/agno` on `PYTHONPATH`, after printing `agno.__file__` to confirm the branch source. Serving examples were imported from a temporary working directory; no server or live model conversation was started by these runs.

### manager_diagnostics.py

**Status:** PASS

**Description:** Constructs a manager with a workspace against a temporary SQLite database, prints the served and registry component lists, and runs the diagnostics. No model calls.

**Result:** Served agents are platform-builder, platform-manager and platform-engineer; served team is os-manager. The registry's agent list is empty and its tool palette holds only the declared calculator. Diagnostics returned WARN: live database PASS, authorization WARN because it is disabled in this demo.

---

### basic_manager.py

**Status:** PASS (constructed, not served)

**Description:** Imported the module to assemble the OS and its FastAPI app without starting the server or calling a model.

**Result:** OS Manager (os-manager) with two members, Platform Builder and Platform Manager; registry agents empty; the FastAPI app assembled. A live conversation was not run.

---

### manager_with_resources.py

**Status:** PASS (constructed, not served)

**Description:** Imported the module to assemble the OS with a notebook, knowledge, learning and a workspace attached to the manager.

**Result:** OS Manager with three members, Platform Engineer included because a workspace is configured; registry agents empty; the FastAPI app assembled. A live conversation was not run.

---

### End-to-end over HTTP

**Status:** PASS (28/28)

**Description:** A scripted model drives a server on a throwaway PostgreSQL database with JWT authorization, user isolation, MCP and the scheduler enabled. Checks cover token refusal and scoping on `teams:os-manager:run`, session isolation for list, read and continue, SSE streaming, delegation from OS Manager to Platform Manager's diagnostics, Platform Builder publishing a palette component that then runs, Platform Builder refusing to compose a manager member, MCP over streamable HTTP, sixteen concurrent runs, resync identity, reserved-id refusal from a second OS on the same database, a Slack interface and an MCP tool bound to `agent_os.manager` after construction, and refusal of an async database.

**Result:** All 28 checks passed. This establishes runtime and tool behaviour, not live-model answer quality.

---
