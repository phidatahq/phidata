# Compaction Cookbooks

Recipes demonstrating Agno's Context Compaction features to keep long conversations within LLM context windows while preserving history and searchability.

## Cookbooks Overview

| File | Description |
| :--- | :--- |
| `compaction.py` | Basic compaction setup using `compaction=True` and `Compaction(uncompacted_runs=...)`. |
| `compaction_manual.py` | Manual compaction on demand with `agent.compact()`. |
| `compaction_thresholds.py` | Configure proactive compaction triggers with `compact_at_tokens`. |
| `compaction_threshold_room.py` | Sizing thresholds to maintain headroom between compact cycles. |
| `compaction_tail_budget.py` | Size-bounded tail retention using `uncompacted_tokens`. |
| `compaction_token_counter.py` | Custom and model-driven token counting strategies. |
| `compaction_async_token_counter.py` | Asynchronous token counting with safety margins in async agents. |
| `compaction_searchable_archive.py` | Enabling the agent to search through archived/compacted history. |
| `compaction_events.py` | Streaming compaction lifecycle events (`CompactionStarted`, `CompactionCompleted`). |
| `compaction_async.py` | Compaction on the asynchronous path (`acompact()`, `arun()`). |
| `compaction_with_tools.py` | Preserving tool call pairs intact during fold boundaries. |
| `compaction_anthropic.py` | Compaction with Anthropic Claude models. |
| `compaction_anthropic_thinking.py` | Compaction handling extended thinking blocks and tool executions. |

## Prerequisites

- Python virtual environment with dependencies (`.venv`).
- PostgreSQL with pgvector (for database persistence examples).
- Environment variables: `OPENAI_API_KEY` (and `ANTHROPIC_API_KEY` for Claude examples).

## Running Cookbooks

```bash
.venv/bin/python cookbook/02_agents/03_context_management/compaction/compaction.py
```
