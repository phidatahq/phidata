"""Translate Claude compaction notifications and correlate stored transcript content."""

from copy import deepcopy
from time import time_ns
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from agno.run.agent import CompactionCompletedEvent, CompactionStartedEvent
from agno.utils.log import log_warning

CompactionEvent = Union[CompactionStartedEvent, CompactionCompletedEvent]


class CompactionTracker:
    def __init__(self, events: List[CompactionEvent], **identity: Any) -> None:
        self.events = events
        self.identity = identity
        self.pending: Dict[Optional[str], CompactionStartedEvent] = {}
        self.queued: List[CompactionEvent] = []
        self.boundaries: Dict[str, CompactionCompletedEvent] = {}
        self.sdk_session_id: Optional[str] = None

    def _append(self, event: CompactionEvent) -> None:
        self.events.append(event)
        self.queued.append(event)

    def _start(self, parent: Optional[str], trigger: Optional[str] = None) -> None:
        if parent in self.pending:
            return
        event = CompactionStartedEvent(
            **self.identity,
            compaction_id=str(uuid4()),
            parent_tool_call_id=parent,
            trigger=trigger,
            timestamp_ns=time_ns(),
        )
        self.pending[parent] = event
        self._append(event)

    async def pre_compact(self, input_data: Any, tool_use_id: Any, context: Any) -> Dict[str, Any]:
        # Hooks do not always identify a subagent. Only use an explicitly reported parent.
        self._start(input_data.get("parent_tool_use_id"), input_data.get("trigger"))
        return {}

    def install(self, sdk: Any, options: Any) -> None:
        if not hasattr(sdk, "HookMatcher"):
            return
        # Preserve the caller's hook lists and callbacks, including their return values.
        hooks = dict(getattr(options, "hooks", None) or {})
        hooks["PreCompact"] = [*hooks.get("PreCompact", []), sdk.HookMatcher(hooks=[self.pre_compact])]
        options.hooks = hooks

    def observe(self, message: Any) -> List[CompactionEvent]:
        data = getattr(message, "data", None) or {}
        if session_id := getattr(message, "session_id", None) or data.get("session_id"):
            self.sdk_session_id = session_id
        parent = getattr(message, "parent_tool_use_id", None) or data.get("parent_tool_use_id")
        subtype = getattr(message, "subtype", None)
        if subtype == "status" and data.get("status") == "compacting":
            self._start(parent)
        elif subtype == "compact_boundary":
            metadata = data.get("compact_metadata") or {}
            started = self.pending.pop(parent, None)
            completed = CompactionCompletedEvent(
                **self.identity,
                compaction_id=started.compaction_id if started else str(uuid4()),
                trigger=metadata.get("trigger") or (started.trigger if started else None),
                timestamp_ns=time_ns(),
                parent_tool_call_id=parent,
                tokens_before=metadata.get("pre_tokens"),
                tokens_after=metadata.get("post_tokens"),
            )
            self._append(completed)
            if boundary_id := getattr(message, "uuid", None) or data.get("uuid"):
                self.boundaries[boundary_id] = completed
        events, self.queued = self.queued, []
        return events

    async def enrich_from_store(self, store: Any) -> None:
        """Read finalized transcript writes without making content capture a run dependency."""
        from agno.agents.claude.session_store import AgnoSessionStore

        if not isinstance(store, AgnoSessionStore) or not self.sdk_session_id or not self.boundaries:
            return
        key = {"session_id": self.sdk_session_id}
        try:
            self._enrich(await store.load(key) or [])
            # Subagent transcripts live under separate keys. Match only exact boundary UUIDs.
            if any(event.parent_tool_call_id and event.summary is None for event in self.boundaries.values()):
                for subpath in await store.list_subkeys(key):
                    self._enrich(await store.load({**key, "subpath": subpath}) or [])
        except Exception:
            log_warning("Could not load compaction transcript content; lifecycle metadata is still available.")

    @staticmethod
    def _message(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        message = entry.get("message")
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            return None
        content = deepcopy(message.get("content"))
        if isinstance(content, list):
            # Thinking blocks are not conversation content for this trace payload.
            content = [
                block
                for block in content
                if not isinstance(block, dict) or block.get("type") not in ("thinking", "redacted_thinking")
            ]
        return {"role": message["role"], "content": content}

    def _enrich(self, entries: List[Dict[str, Any]]) -> None:
        by_id = {entry["uuid"]: entry for entry in entries if entry.get("uuid")}
        for boundary_id, completed in self.boundaries.items():
            boundary = by_id.get(boundary_id)
            if not boundary or boundary.get("subtype") != "compact_boundary":
                continue
            summaries = [
                entry for entry in entries if entry.get("isCompactSummary") and entry.get("parentUuid") == boundary_id
            ]
            if len(summaries) == 1 and (summary := self._message(summaries[0])) is not None:
                completed.summary = summary["content"]
            # logicalParentUuid points to the conversation tip before the boundary reset.
            current = boundary.get("logicalParentUuid")
            messages = []
            seen = {boundary_id}
            while current:
                if current in seen or current not in by_id:
                    # Incomplete or rewritten ancestry cannot establish the input context.
                    break
                seen.add(current)
                entry = by_id[current]
                if (message := self._message(entry)) is not None:
                    messages.append(message)
                current = entry.get("parentUuid")
            else:
                if messages:
                    completed.recorded_context = list(reversed(messages))
