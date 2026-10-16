# TEST_LOG

### basic.py

**Status:** PASS (3 of 4 runs)

**Description:** Sync, sync + streaming, async and async + streaming responses on `qwen3-coder-30b`.

**Result:** The sync, sync streaming and first async runs return full responses. The final async streaming run fails with `Event loop is closed`, because it is the second `asyncio.run()` on the same Agent. The same failure reproduces with a plain `OpenAILike` model reused across two `asyncio.run()` calls, so it is not specific to this provider.

---

### tool_use.py

**Status:** PASS (3 of 4 runs)

**Description:** `WebSearchTools` with sync, sync + streaming, async and async + streaming runs on `qwen3-coder-30b`.

**Result:** The model issues `search_news` and `web_search` tool calls and answers from the results. The final async streaming run hits the same `Event loop is closed` error as `basic.py`.

---

### Additional check (not a cookbook file)

**Status:** PASS

**Description:** A local `get_weather` tool, a streamed answer and an async run through the `linkrra:qwen3-coder-30b` string syntax, against `qwen3-coder-30b`, `gpt-oss-20b` and `gemma-4-26b-a4b-it`.

**Result:** All three models called `get_weather` and answered from its result. Streaming returned the expected text on all three. The string-syntax async run returned `pong`.
