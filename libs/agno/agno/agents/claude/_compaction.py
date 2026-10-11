"""Translate Claude compaction notifications without retaining transcript content."""

from time import time_ns
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from agno.run.agent import CompactionCompletedEvent, CompactionStartedEvent

CompactionEvent = Union[CompactionStartedEvent, CompactionCompletedEvent]


class CompactionTracker:
    def __init__(self, events: List[CompactionEvent], **identity: Any) -> None:
        self.events = events
        self.identity = identity
        self.pending: Dict[Optional[str], CompactionStartedEvent] = {}
        self.queued: List[CompactionEvent] = []

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
        parent = getattr(message, "parent_tool_use_id", None) or data.get("parent_tool_use_id")
        subtype = getattr(message, "subtype", None)
        if subtype == "status" and data.get("status") == "compacting":
            self._start(parent)
        elif subtype == "compact_boundary":
            metadata = data.get("compact_metadata") or {}
            started = self.pending.pop(parent, None)
            self._append(
                CompactionCompletedEvent(
                    **self.identity,
                    compaction_id=started.compaction_id if started else str(uuid4()),
                    trigger=metadata.get("trigger") or (started.trigger if started else None),
                    timestamp_ns=time_ns(),
                    parent_tool_call_id=parent,
                    tokens_before=metadata.get("pre_tokens"),
                    tokens_after=metadata.get("post_tokens"),
                )
            )
        events, self.queued = self.queued, []
        return events
