from types import SimpleNamespace

import pytest

from agno.agents.claude._compaction import CompactionTracker


def message(subtype, parent=None, **data):
    return SimpleNamespace(subtype=subtype, data=data, parent_tool_use_id=parent)


@pytest.mark.asyncio
async def test_hooks_are_composed_without_mutating_callers():
    calls = []

    async def user_hook(*args):
        calls.append(args)
        return {"suppressOutput": True}

    original = {"PreCompact": [SimpleNamespace(hooks=[user_hook], matcher="manual")]}
    options = SimpleNamespace(hooks=original)
    tracker = CompactionTracker([], run_id="run")
    tracker.install(SimpleNamespace(HookMatcher=SimpleNamespace), options)
    assert options.hooks is not original
    assert len(original["PreCompact"]) == 1
    assert options.hooks["PreCompact"][0] is original["PreCompact"][0]
    assert await options.hooks["PreCompact"][0].hooks[0]({}, None, {}) == {"suppressOutput": True}
    await options.hooks["PreCompact"][1].hooks[0]({"trigger": "manual"}, None, {})
    assert len(calls) == 1
    assert tracker.events[0].trigger == "manual"


@pytest.mark.asyncio
async def test_parallel_and_repeated_compactions_keep_explicit_parent_ids():
    events = []
    tracker = CompactionTracker(events)
    await tracker.pre_compact({"trigger": "auto", "parent_tool_use_id": "a"}, None, {})
    await tracker.pre_compact({"trigger": "manual", "parent_tool_use_id": "b"}, None, {})
    tracker.observe(message("compact_boundary", "b", compact_metadata={"pre_tokens": 20}))
    tracker.observe(message("compact_boundary", "a", compact_metadata={"pre_tokens": 40}))
    assert events[0].compaction_id == events[3].compaction_id
    assert events[1].compaction_id == events[2].compaction_id
    assert events[2].parent_tool_call_id == "b"
    assert events[2].trigger == "manual"
    tracker.observe(message("status", "a", status="compacting"))
    assert events[-1].compaction_id != events[0].compaction_id


def test_completion_without_start_and_noop_do_not_invent_lifecycle():
    events = []
    tracker = CompactionTracker(events)
    assert tracker.observe(message("status", status=None)) == []
    assert tracker.observe(message("result", result="Not enough messages to compact")) == []
    completed = tracker.observe(message("compact_boundary", compact_metadata={"trigger": "manual"}))
    assert len(completed) == 1
    assert completed[0].event == "CompactionCompleted"
    assert completed[0].tokens_before is None


@pytest.mark.asyncio
async def test_start_without_boundary_stays_incomplete():
    tracker = CompactionTracker([])
    await tracker.pre_compact({"trigger": "auto"}, None, {})
    events = tracker.observe(message("result", is_error=True))
    assert [e.event for e in events] == ["CompactionStarted"]
    assert None in tracker.pending
