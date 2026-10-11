import json
from datetime import datetime, timezone
from types import SimpleNamespace

from agno.os.routers.traces.schemas import TraceNode


def span(**attributes):
    return SimpleNamespace(
        span_id="compaction-span",
        name="ClaudeAgent.compaction",
        attributes={"openinference.span.kind": "CHAIN", **attributes},
        duration_ms=125,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        status_code="OK",
    )


def test_compaction_info_and_metadata_reach_trace_node():
    node = TraceNode.from_span(
        span(
            **{
                "agno.compaction.id": "compact-1",
                "agno.compaction.trigger": "auto",
                "agno.compaction.status": "completed",
                "agno.compaction.tokens_before": 12000,
                "agno.compaction.tokens_after": 0,
                "agno.compaction.duration_unknown": False,
                "agno.tool.parent_call_id": "delegate-1",
                "input.value": '{"operation":"conversation_compaction","trigger":"auto","tokens_before":12000}',
                "output.value": '{"status":"completed","tokens_after":0}',
            }
        )
    )
    assert json.loads(node.input)["tokens_before"] == 12000
    assert json.loads(node.output)["status"] == "completed"
    assert node.metadata == {
        "compaction_id": "compact-1",
        "trigger": "auto",
        "status": "completed",
        "tokens_before": 12000,
        "tokens_after": 0,
        "duration_unknown": False,
        "parent_tool_call_id": "delegate-1",
    }


def test_existing_compaction_spans_gain_metadata_without_fabricated_values():
    node = TraceNode.from_span(span(**{"agno.compaction.id": "compact-1", "agno.compaction.tokens_before": 1000}))
    assert node.metadata == {"compaction_id": "compact-1", "tokens_before": 1000}
    assert node.input is None and node.output is None


def test_other_chain_spans_keep_existing_metadata():
    node = TraceNode.from_span(span(**{"agno.workflow.description": "workflow", "agno.workflow.steps_count": 2}))
    assert node.metadata == {"description": "workflow", "steps_count": 2}
