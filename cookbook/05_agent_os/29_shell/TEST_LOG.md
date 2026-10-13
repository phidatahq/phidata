# Test log

Executed 2026-10-13 with the development environment and this branch's `libs/agno` on `PYTHONPATH`.

### shell_diagnostics.py

**Status:** PASS

**Description:** Constructs a shell with a workspace against a temporary SQLite database, prints the served and registry component lists, and runs the diagnostics. No model calls.

**Result:** Served agents are platform-builder, platform-manager and platform-engineer; served team is agno; the registry's agent list is empty and its tool palette holds only the declared calculator. Diagnostics returned WARN with a live database PASS and an authorization WARN (disabled in this demo), as expected.

---

### basic_shell.py

**Status:** PASS (constructed, not served)

**Description:** Imported the module to assemble the OS and its FastAPI app without starting the server or calling a model.

**Result:** Two member agents and the agno team registered; registry agents empty. Serving and a live conversation need an OpenAI key and were not run.

---

### shell_with_resources.py

**Status:** PASS (constructed, not served)

**Description:** Imported the module to assemble the OS with a notebook, knowledge, learning and a workspace attached to the shell.

**Result:** Three member agents (engineer present because a workspace is configured) and the agno team registered; registry agents empty. Serving and a live conversation were not run.

---
