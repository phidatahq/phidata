# Test Log -- 04_tools

**Tested:** 2026-02-13
**Environment:** .venvs/demo/bin/python, pgvector: running

---

### 01_callable_tools.py

**Status:** PASS
**Tier:** untagged
**Description:** Demonstrates 01 callable tools. Ran successfully and produced expected output.
**Result:** Completed successfully in 17s.

---

### 02_session_state_tools.py

**Status:** PASS
**Tier:** untagged
**Description:** Demonstrates 02 session state tools. Ran successfully and produced expected output.
**Result:** Completed successfully in 7s.

---

### 03_team_callable_members.py

**Status:** PASS
**Tier:** untagged
**Description:** Demonstrates 03 team callable members. Ran successfully and produced expected output.
**Result:** Completed successfully in 87s.

---

### 04_tools_with_literal_type_param.py

**Status:** PASS
**Tier:** untagged
**Description:** Demonstrates using typing.Literal for tool parameters with predefined values. Tests both Toolkit methods and standalone functions with Literal type hints.
**Result:** JSON schema correctly generates enum constraints for Literal types.

---

### tool_call_limit.py

**Status:** PASS
**Tier:** untagged
**Description:** Demonstrates tool call limit. Ran successfully and produced expected output.
**Result:** Completed successfully in 13s.

---

### tool_choice.py

**Status:** TIMEOUT
**Tier:** untagged
**Description:** Demonstrates tool choice. Timed out after 120s - likely making many API calls or stuck.
**Result:** Timed out after 120s.

---

### 05_deferred_tools_tool_search.py

**Status:** PASS
**Tier:** untagged
**Description:** Two deferred toolkits on `gpt-5.4-mini`. The model called the always-loaded `list_alerts`, found `search_tickets` and `assign_ticket` with the hosted tool search, and called both. Tested 2026-10-21 with `.venv/bin/python`.
**Result:** Completed successfully in 9s.

---

### 06_tool_search_token_savings.py

**Status:** PASS
**Tier:** untagged
**Description:** Counted one request for 60 tools in 6 toolkits with the OpenAI token counting endpoint: 3,353 input tokens loaded, 1,375 deferred with the index (59% fewer). Tested 2026-10-21 with `.venv/bin/python`.
**Result:** Completed successfully in 2s.

---
