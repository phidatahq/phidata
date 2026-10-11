"""Verify Claude compaction spans in Agno's tracing database.

Requires claude-agent-sdk, authentication, and editable Agno and OpenInference
checkouts with external-agent compaction tracing support.

    .venv/bin/python cookbook/frameworks/claude-agent-sdk/tracing_compaction.py
    .venv/bin/python cookbook/frameworks/claude-agent-sdk/tracing_compaction.py --stream

Manual /compact uses the same lifecycle signals as automatic compaction. SQLite
is used for this local test; use PostgreSQL in production.
"""

import argparse
import asyncio
import json
from tempfile import TemporaryDirectory
from uuid import uuid4

from opentelemetry import trace

from agno.agents.claude import ClaudeAgent
from agno.db.sqlite import SqliteDb
from agno.os.routers.traces.schemas import TraceNode
from agno.run.agent import RunOutput
from agno.tracing import setup_tracing


async def main(stream: bool) -> None:
    db = SqliteDb(db_file="tmp/claude-compaction-traces.db")
    setup_tracing(db=db)
    session_id = str(uuid4())
    with TemporaryDirectory(prefix="agno-compaction-trace-") as directory:
        agent = ClaudeAgent(
            id="claude-compaction-trace",
            model="claude-sonnet-4-6",
            cwd=directory,
            db=db,
            max_turns=2,
            max_budget_usd=0.5,
        )
        document = "\n".join(
            f"Record {index}: The project codename is tangerine."
            for index in range(800)
        )
        for prompt in (
            "Remember this document and reply with just OK:\n" + document,
            "What is the project codename? Reply with just the name.",
        ):
            result = await agent.arun(prompt, session_id=session_id)
            assert result.status.value.lower() == "completed", result.content

        if stream:
            output = None
            async for event in agent.arun(
                "/compact", stream=True, yield_run_output=True, session_id=session_id
            ):
                if isinstance(event, RunOutput):
                    output = event
                elif event.event.startswith("Compaction"):
                    print(event.event)
        else:
            output = await agent.arun("/compact", session_id=session_id)
        assert output is not None and output.status.value.lower() == "completed"

    trace.get_tracer_provider().force_flush()
    events = (output.metadata or {}).get("compaction_events", [])
    assert [event["event"] for event in events] == [
        "CompactionStarted",
        "CompactionCompleted",
    ], events
    record = db.get_trace(run_id=output.run_id)
    assert record is not None
    spans = db.get_spans(trace_id=record.trace_id)
    root = next(span for span in spans if span.parent_span_id is None)
    compactions = [span for span in spans if span.name == "ClaudeAgent.compaction"]
    assert len(compactions) == 1
    span = compactions[0]
    assert span.parent_span_id == root.span_id
    assert span.status_code == "OK"
    assert span.attributes["agno.compaction.trigger"] == "manual"
    assert span.attributes["agno.compaction.tokens_before"] > 0
    assert span.duration_ms > 0
    node = TraceNode.from_span(span)
    recorded_context = json.loads(node.input)
    assert isinstance(recorded_context, list) and recorded_context
    assert "tangerine" in node.input.lower()
    assert node.output and "tangerine" in node.output.lower()
    assert node.metadata["input_source"] == "recorded_conversation"
    assert node.metadata["output_source"] == "transcript_summary"
    assert node.metadata["trigger"] == "manual"
    assert node.metadata["tokens_before"] > 0
    print("ClaudeAgent.run -> ClaudeAgent.compaction")
    print("Compaction duration (ms):", span.duration_ms)
    print("Tokens before:", span.attributes["agno.compaction.tokens_before"])
    print("Recorded context messages:", len(recorded_context))
    print("Summary characters:", len(node.output))
    print("Trace ID:", record.trace_id)
    print("Verified compaction trace in tmp/claude-compaction-traces.db")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(main(args.stream), timeout=180))
