"""Trace Claude subagent tools into Agno's database with their actual parents.

Requires claude-agent-sdk and an openinference-instrumentation-agno checkout
with external tool lineage support, installed in the same Python environment.

    .venv/bin/python cookbook/frameworks/claude-agent-sdk/tracing_subagents.py

SQLite is used for this local verification; use PostgreSQL in production.
"""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from claude_agent_sdk import AgentDefinition
from opentelemetry import trace

from agno.agents.claude import ClaudeAgent
from agno.db.sqlite import SqliteDb
from agno.run.agent import RunOutput
from agno.tracing import setup_tracing


async def main() -> None:
    db = SqliteDb(db_file="tmp/claude-nested-traces.db")
    setup_tracing(db=db)
    run_id = str(uuid4())
    with TemporaryDirectory(prefix="agno-trace-probe-") as directory:
        Path(directory, "probe.txt").write_text("nested_read_probe\n")
        agent = ClaudeAgent(
            name="Claude trace probe",
            model="claude-sonnet-4-6",
            db=db,
            cwd=directory,
            allowed_tools=["Agent", "Bash", "Read"],
            max_turns=8,
            max_budget_usd=1.0,
            options_kwargs={
                "agents": {
                    "trace-probe": AgentDefinition(
                        description="Run the tracing verification tools.",
                        prompt=(
                            "Run Bash with `printf nested_shell_probe` once, then Read probe.txt "
                            "in the working directory. Report both outputs. Do not modify files."
                        ),
                        tools=["Bash", "Read"],
                        model="haiku",
                    )
                }
            },
        )
        output = None
        async for event in agent.arun(
            "Use the trace-probe subagent to perform its verification. After it finishes, "
            "run Bash yourself with `printf main_shell_probe` once. Then report the three outputs.",
            stream=True,
            yield_run_output=True,
            run_id=run_id,
            session_id=run_id,
            user_id="tracing-demo",
        ):
            if isinstance(event, RunOutput):
                output = event

    trace.get_tracer_provider().force_flush()
    assert output is not None and output.status.value.lower() == "completed", (
        "Claude run did not complete"
    )
    record = db.get_trace(run_id=run_id)
    assert record is not None, "No trace persisted; check the instrumenter installation"
    spans = db.get_spans(trace_id=record.trace_id)
    root = next(span for span in spans if span.parent_span_id is None)
    tool_spans = {
        span.attributes["tool_call.id"]: span
        for span in spans
        if "tool_call.id" in span.attributes
    }
    nested = [
        span
        for span in tool_spans.values()
        if span.attributes.get("agno.tool.parent_call_id")
    ]
    assert nested, (
        "No nested tools recorded; check both Agno and the instrumenter have lineage support"
    )
    for span in nested:
        parent = tool_spans[span.attributes["agno.tool.parent_call_id"]]
        assert span.parent_span_id == parent.span_id
    assert any(
        span.name == "Bash" and span.parent_span_id == root.span_id
        for span in tool_spans.values()
    )
    assert {"Bash", "Read"}.issubset({span.name for span in nested})
    assert all(span.status_code == "OK" for span in spans)

    def show_tree(parent_id: str | None, depth: int = 0) -> None:
        for span in sorted(spans, key=lambda span: span.start_time):
            if span.parent_span_id == parent_id:
                print("  " * depth + span.name)
                show_tree(span.span_id, depth + 1)

    show_tree(None)
    print("Trace ID:", record.trace_id)
    print(
        "Verified nested tool spans and top-level sibling in tmp/claude-nested-traces.db"
    )


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=120))
