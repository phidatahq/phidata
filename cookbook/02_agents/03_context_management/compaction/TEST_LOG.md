# Test Log: Compaction Cookbooks

Test results for context compaction recipes under `cookbook/02_agents/03_context_management/compaction/`.

### compaction.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests basic compaction with `Compaction(uncompacted_runs=2)` and `agent.compact()`.

---

### compaction_manual.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests manual session folding with `agent.compact()` and inspects compaction status results.

---

### compaction_thresholds.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests automatic threshold folding at token boundaries with `compact_at_tokens`.

---

### compaction_threshold_room.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests headroom calculation after compaction to prevent repeated immediate folding.

---

### compaction_tail_budget.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests size-based uncompacted tail retention using `uncompacted_tokens`.

---

### compaction_token_counter.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests custom token counting functions and model token counting (`use_model_token_count=True`).

---

### compaction_async_token_counter.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests async token counter awaiting in async runs.

---

### compaction_searchable_archive.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests agent retrieval from stored messages using the compaction archive search tool.

---

### compaction_events.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests streaming compaction events in run event generator.

---

### compaction_async.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests asynchronous compaction execution path (`acompact()`).

---

### compaction_with_tools.py

**Status:** PENDING (requires local postgres + API key)

**Description:** Tests preservation of tool call message boundaries across compaction folds.

---

### compaction_anthropic.py

**Status:** PENDING (requires ANTHROPIC_API_KEY)

**Description:** Tests compaction formatting against Claude messages payload.

---

### compaction_anthropic_thinking.py

**Status:** PENDING (requires ANTHROPIC_API_KEY)

**Description:** Tests compaction with thinking budget blocks.

---
