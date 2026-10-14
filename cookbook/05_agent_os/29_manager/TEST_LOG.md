# Test log

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
