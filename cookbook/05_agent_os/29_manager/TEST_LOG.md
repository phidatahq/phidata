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
## Review corrections — 2026-10-14

### manager_diagnostics.py

**Status:** PASS

**Description:** Ran the model-free diagnostics cookbook after correcting Slack credential resolution and component ID checks. Database, components, registry and interfaces passed. Authorization reported WARN, and the absent `OPENAI_API_KEY` correctly reported FAIL.

**Result:** The script completed successfully without model calls. The report's overall FAIL reflects the missing required environment variable, not a script failure.

---

### Manager authorization and diagnostics regressions

**Status:** PASS

**Description:** 168 manager and diagnostics tests passed, including 57 new cases. Coverage includes the manager and every specialist, JWT and managed-role authority, service-account tokens with and without JWT authorization, continuation refusal, schedule target checks, MCP and default A2A gates, Slack environment/explicit credentials, and component ID namespaces. Existing ordinary agents remain runnable by ordinary grants.

**Result:** Selected regression cases were also run against the reviewed commit: 19 failed and 22 passed, confirming the tests detect the original issues. The final authorization, service-account and diagnostics selection passed 297 tests. Full formatting and validation passed with isolated validation dependencies. No paid model calls or live Slack delivery checks were performed.

---

## Caller permissions — 2026-10-14

This supersedes the admin-only manager policy recorded above. Ordinary component
run grants now admit the conversation; protected tools authorize each operation.

### manager_user_access.py

**Status:** PASS (construction only)

**Description:** Loaded the example with a temporary verification key and working
directory. The managed role grants Alice manager access, math-helper access and
diagnostics, without component publishing or schedule creation.

**Result:** The AgentOS app constructed successfully. No model calls or live JWT
issuer integration were performed. The diagnostics cookbook was also rerun and
completed; its missing `OPENAI_API_KEY` check still reports the expected FAIL.

---

### Caller authorization regressions and validation

**Status:** PASS

**Description:** Added 36 offline regressions covering allowed and denied target
runs, direct and delegated builder writes, JWT/role/service-account decisions,
MCP calls, durable jobs, queued continuation authority, scheduled execution,
concurrent callers, parallel synchronous delegation, cached results, forged
snapshots and preservation of the parent policy through mounted applications.
The existing manager tests now verify ordinary run grants can reach the manager.

**Result:** The broad affected run passed 6,375 tests with 24 skips. Its one failing
assertion expected the old queued-continuation payload; it was updated for the
persisted authority and passes in the 77-test targeted rerun. Final selections
passed 674 MCP/authorization/continuation tests, 86 provider/service-account tests,
and 278 workspace/authorization tests (one skip). Formatting and full validation
passed with the isolated validation dependencies. An attempted all-tools run
could not collect unrelated optional integrations; the affected selection excludes
three Telegram files whose optional dependency is unavailable.

---

## OSManager API and fixed identity — 2026-10-15

These results supersede the earlier configurable-ID and Platform Engineer descriptions.

### basic_manager.py

**Status:** PASS

**Description:** Constructed the example in a temporary directory without model calls.

**Result:** OS Manager has the fixed `os-manager-internal` ID, exactly two members, and its model is available in the build registry. No privileged manager tools are exposed to builds.

---

### manager_builds_agents.py

**Status:** PASS

**Description:** Constructed the declared-registry example without model calls.

**Result:** The fixed manager team reuses the declared model and keeps Platform Builder and Platform Manager as its two members.

---

### manager_with_resources.py

**Status:** PASS

**Description:** Constructed the notebook, learning, root and optional docs example in a temporary directory. No model or live MCP calls were made.

**Result:** Platform Manager receives read-only source tools and the opt-in Agno docs MCP toolkit. There is no Platform Engineer. Separate regressions verify file exclusions and stubbed MCP connection/cleanup.

---

### manager_user_access.py

**Status:** PASS

**Description:** Constructed the example using a temporary JWT verification key, without model calls.

**Result:** The managed role uses the new reserved team ID. Regression tests verify that run, discovery and session-reading grants remain separate and another user's sessions stay inaccessible.

---

### manager_diagnostics.py

**Status:** PASS

**Description:** Executed the model-free diagnostics example.

**Result:** The command completed. Its overall report is FAIL because the required `OPENAI_API_KEY` is absent; this is expected and is not a failed execution.

---

### OSManager regression and validation suites

**Status:** PASS

**Description:** Added 27 parametrized regression cases for reserved IDs, disabled-manager and resync protections, metadata on discovery/detail/run responses, model-only builds, docs MCP lifecycle, and independent run/read/session permissions. Updated existing tests for the API, IDs and two-member composition, preserving source confinement and authorization coverage.

**Result:** The broad affected suite passed **6,082 tests, 24 skipped**. The final manager/authorization/registry/component API selection passed **563 tests, 14 skipped** after the final reservation checks; selections overlap. The focused manager/authorization selection passed **182 tests**. Three unrelated Telegram files were excluded because their optional dependency is unavailable. Required `scripts/format.sh` and `scripts/validate.sh` pass using `.venv` with isolated validation dependencies; mypy covers **1,126 framework files and 21 CLI files**. Unrelated formatter-only changes were removed. No paid model, live PostgreSQL, live Slack delivery or live docs MCP calls were made.

---
