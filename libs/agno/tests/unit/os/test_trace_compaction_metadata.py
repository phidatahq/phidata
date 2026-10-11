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


def test_compaction_metadata_does_not_fabricate_input_output():
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
            }
        )
    )
    assert node.input is None and node.output is None
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


def test_transcript_payloads_populate_info_with_source_metadata():
    node = TraceNode.from_span(
        span(
            **{
                "agno.compaction.id": "c1",
                "agno.compaction.input_source": "recorded_conversation",
                "agno.compaction.output_source": "transcript_summary",
                "input.value": '[{"role": "user", "content": "Remember tangerine"}]',
                "output.value": "The codename is tangerine.",
            }
        )
    )
    assert "Remember tangerine" in node.input
    assert node.output == "The codename is tangerine."
    assert node.metadata["input_source"] == "recorded_conversation"
    assert node.metadata["output_source"] == "transcript_summary"
