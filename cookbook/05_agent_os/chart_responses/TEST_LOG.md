# Test Log — chart_responses

Tested 2026-10-15 on branch `as/charts-example` with `.venvs/demo/bin/python`,
`OPENAI_API_KEY` set, and `gpt-5.6-luna`. Each example was imported to confirm
the AgentOS wiring, then the agent or team was run directly with a quick prompt
and the response was parsed for fenced chart blocks.

### agentos_chart_responses.py

**Status:** PASS

**Description:** Single agent with ChartTools. Imported the module and confirmed
the agent, quick prompts, and app are registered.

**Result:** Wiring valid. Chart behaviour for this file is covered by the
toolkit unit tests in `libs/agno/tests/unit/tools/test_chart.py`.

---

### agentos_chart_team.py

**Status:** PASS

**Description:** Ran the Growth Review Team with "Review the last 30 days of
usage and cost." Checked that each member called its data tool before
`create_chart`, and that the leader's content kept both member chart blocks.

**Result:** Two chart blocks in the leader response. Usage Analyst called
`get_daily_usage` then `create_chart` and produced a 30-row line chart with
runs, sessions, and active_users keyed by date. Cost Analyst called
`get_spend_by_model` then `create_chart` and produced a 3-row bar-stacked chart
of input and output tokens by model. The leader added a heading above each
chart and closed with a three-bullet summary. Run time about 59 seconds.

---

### agentos_platform_dashboard.py

**Status:** PASS

**Description:** Called `seed_activity()` to run the worker three times with
tracing on, then ran the dashboard agent with "Chart token usage by day and the
model mix." Checked tool order and chart data.

**Result:** Tool order was `get_platform_metrics`, `create_chart`,
`create_chart`. The bar chart used the real date and token total from the
metrics payload, and the pie chart used the real model mix (3 runs on
gpt-5.6-luna). The agent stated the window and noted that the backend returned
activity for only one day. Run time about 24 seconds.

---
