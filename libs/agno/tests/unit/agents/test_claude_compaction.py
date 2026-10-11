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


def entry(uuid, parent, text, **extra):
    return {"uuid": uuid, "parentUuid": parent, "message": {"role": "user", "content": text}, **extra}


def boundary(uuid, tip):
    return {"uuid": uuid, "parentUuid": None, "logicalParentUuid": tip, "subtype": "compact_boundary"}


def test_repeated_compactions_match_summary_and_message_ancestry():
    tracker = CompactionTracker([])
    first = tracker.observe(message("compact_boundary", uuid="c1"))[0]
    second = tracker.observe(message("compact_boundary", uuid="c2"))[0]
    entries = [
        entry("u1", None, "original context"),
        entry("unrelated", None, "another branch"),
        boundary("c1", "u1"),
        entry("s1", "c1", "first summary", isCompactSummary=True),
        entry("u2", "s1", "new context"),
        boundary("c2", "u2"),
        entry("s2", "c2", "second summary", isCompactSummary=True),
    ]
    tracker._enrich(entries)
    assert first.recorded_context == [{"role": "user", "content": "original context"}]
    assert first.summary == "first summary"
    assert second.recorded_context == [
        {"role": "user", "content": "first summary"},
        {"role": "user", "content": "new context"},
    ]
    assert second.summary == "second summary"
    restored = type(second).from_dict(second.to_dict())
    assert restored.recorded_context == second.recorded_context
    assert restored.summary == second.summary


@pytest.mark.parametrize("tip", ["missing", "c1", None])
def test_missing_or_cyclic_ancestry_does_not_fabricate_input(tip):
    tracker = CompactionTracker([])
    completed = tracker.observe(message("compact_boundary", uuid="c1"))[0]
    tracker._enrich([boundary("c1", tip), entry("s1", "c1", "summary", isCompactSummary=True)])
    assert completed.recorded_context is None
    assert completed.summary == "summary"


def test_summary_without_matching_boundary_is_not_attached():
    tracker = CompactionTracker([])
    completed = tracker.observe(message("compact_boundary", uuid="c1"))[0]
    tracker._enrich([boundary("c1", None), entry("s2", "c2", "wrong summary", isCompactSummary=True)])
    assert completed.summary is None


def test_context_retains_tool_content_but_excludes_thinking():
    tracker = CompactionTracker([])
    completed = tracker.observe(message("compact_boundary", uuid="c1"))[0]
    blocks = [
        {"type": "thinking", "thinking": "private"},
        {"type": "text", "text": "visible"},
        {"type": "tool_result", "tool_use_id": "tool-1", "content": "result"},
    ]
    tracker._enrich([entry("u1", None, blocks), boundary("c1", "u1")])
    assert completed.recorded_context[0]["content"] == blocks[1:]
    assert len(blocks) == 3


@pytest.mark.asyncio
async def test_transcript_read_failure_keeps_lifecycle(monkeypatch):
    from agno.agents.claude.session_store import AgnoSessionStore

    async def failing(self, key):
        raise RuntimeError("offline")

    monkeypatch.setattr(AgnoSessionStore, "load", failing)
    tracker = CompactionTracker([])
    tracker.sdk_session_id = "s"
    completed = tracker.observe(message("compact_boundary", uuid="c1"))[0]
    await tracker.enrich_from_store(AgnoSessionStore(None, "p", "agno-session"))
    assert completed.event == "CompactionCompleted"
    assert completed.summary is None and completed.recorded_context is None


@pytest.mark.asyncio
async def test_subagent_content_uses_matching_subpath(monkeypatch):
    from agno.agents.claude.session_store import AgnoSessionStore

    async def load(self, key):
        if key.get("subpath") == "subagent":
            return [
                entry("u1", None, "child context"),
                boundary("c1", "u1"),
                entry("s1", "c1", "child summary", isCompactSummary=True),
            ]
        return [entry("s0", "c0", "parent summary", isCompactSummary=True)]

    async def subkeys(self, key):
        return ["subagent"]

    monkeypatch.setattr(AgnoSessionStore, "load", load)
    monkeypatch.setattr(AgnoSessionStore, "list_subkeys", subkeys)
    tracker = CompactionTracker([])
    tracker.sdk_session_id = "s"
    completed = tracker.observe(message("compact_boundary", parent="delegate", uuid="c1"))[0]
    await tracker.enrich_from_store(AgnoSessionStore(None, "p", "agno-session"))
    assert completed.summary == "child summary"
    assert completed.recorded_context[0]["content"] == "child context"
