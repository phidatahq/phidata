"""Deferred tool loading behind provider-side tool search.

A tool marked ``defer_loading`` (on the Function, via ``@tool(defer_loading=True)``, or through a
Toolkit's ``defer_loading`` / ``deferred_tools``) is still sent to the model provider on every
request, but its full definition stays out of the model's context until the model finds it with the
provider's tool search. Agno renders a short index of what can be searched into the system prompt,
next to the toolkit instructions, so the model knows to look.

Deferral is honored only when the model supports tool search (``Model.supports_tool_search()``):
Claude Opus 4.5 / Sonnet 4.5 / Haiku 4.5 and newer (Anthropic, Bedrock, Vertex AI, Foundry), and
GPT-5.4 and newer on the OpenAI Responses API. Everywhere else deferred tools load normally, so a
fallback model still sees every tool.

    agent = Agent(
        model=Claude(id="claude-opus-5-5"),
        tools=[MCPTools(url=SERVICEOPS_URL, defer_loading=True)],
        tool_search=ToolSearch(index="toolkits"),  # optional; on by default when a tool is deferred
    )
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple, Union

from agno.utils.log import log_warning

if TYPE_CHECKING:
    from agno.models.base import Model
    from agno.tools.function import Function
    from agno.tools.toolkit import Toolkit

# Group for deferred tools that do not come from a Toolkit.
_STANDALONE_GROUP = "tools"
# Longest summary kept for one group in the index.
_MAX_SUMMARY_CHARS = 300
# Model ids already warned about loading deferred tools normally, so the warning is not repeated every run.
_warned_models: set = set()


@dataclass
class ToolSearch:
    """How deferred tools are offered to the model.

    Args:
        index: What the system prompt lists about deferred tools.
            "names" (default): one line per toolkit with its summary and the names of its deferred
                tools. Names cost a few tokens each and tell the model what it can search for even
                when a summary does not.
            "toolkits": one line per toolkit with its summary only (names when it has none).
            "none": nothing; the model relies on the tool search tool's own description.
    """

    index: Literal["names", "toolkits", "none"] = "names"


def resolve_tool_search(value: Optional[Union[bool, ToolSearch]]) -> Optional[ToolSearch]:
    """Normalize the Agent/Team ``tool_search`` argument. False turns deferral off."""
    if value is False:
        return None
    if isinstance(value, ToolSearch):
        return value
    return ToolSearch()


def tool_search_to_config(value: Union[bool, ToolSearch]) -> Union[bool, Dict[str, Any]]:
    """The tool_search setting as it is stored in a component config: a bool or the ToolSearch settings."""
    if isinstance(value, ToolSearch):
        return {"index": value.index}
    return bool(value)


def tool_search_from_config(value: Any) -> Optional[Union[bool, ToolSearch]]:
    """The tool_search setting from a stored component config."""
    if isinstance(value, dict):
        return ToolSearch(**{k: v for k, v in value.items() if k == "index"})
    if isinstance(value, bool):
        return value
    return None


def escape_markup(text: str) -> str:
    """Escape angle brackets so text from a toolkit or MCP server cannot open or close prompt tags."""
    return text.replace("<", "&lt;").replace(">", "&gt;")


def summarize(text: Optional[str]) -> Optional[str]:
    """First paragraph of ``text`` on one line, capped at a few hundred characters, markup escaped."""
    if not text:
        return None
    paragraph = text.strip().split("\n\n", 1)[0]
    line = " ".join(paragraph.split())
    if len(line) > _MAX_SUMMARY_CHARS:
        line = line[: _MAX_SUMMARY_CHARS - 3].rstrip() + "..."
    return escape_markup(line) or None


def server_instructions_snippet(entries: List[Tuple[str, str]]) -> Optional[str]:
    """System prompt block for instructions that toolkits pass on from the server behind them.

    ``entries`` are (toolkit name, instructions) pairs, from Toolkit.get_server_instructions(). The text
    is third-party, so its markup is escaped, and the Agent/Team adds the block after resolving state
    variables: placeholders such as {user_id} or $name in it are never filled in.
    """
    if not entries:
        return None
    lines = [
        "<server_instructions>",
        "Instructions from the servers behind some of your tools, describing how to use their tools:",
    ]
    for name, text in entries:
        lines.append(f'<server name="{escape_markup(name)}">')
        lines.append(escape_markup(text.strip()))
        lines.append("</server>")
    lines.append("</server_instructions>")
    return "\n".join(lines)


@dataclass
class _Group:
    name: str
    summary: Optional[str] = None
    tool_names: List[str] = field(default_factory=list)


class DeferredTools:
    """Collects the deferred tools of one run while an Agent or Team parses its tools.

    Deferral is active when tool search is on and the model can search; otherwise deferred tools
    are loaded like any other tool. Nothing is resolved until a deferred tool shows up, so runs
    without one pay nothing.
    """

    def __init__(self, model: "Model", tool_search: Optional[Union[bool, ToolSearch]]):
        self._model = model
        self._tool_search = tool_search
        self.config: Optional[ToolSearch] = None
        self._active: Optional[bool] = None
        # One group per toolkit object (two servers may share a name), plus one for standalone tools
        self._groups: Dict[int, _Group] = {}

    @property
    def active(self) -> bool:
        if self._active is None:
            self.config = resolve_tool_search(self._tool_search)
            supports = getattr(self._model, "supports_tool_search", None)
            self._active = self.config is not None and callable(supports) and bool(supports())
        return self._active

    def add(self, function: "Function", toolkit: Optional["Toolkit"] = None) -> None:
        """Record a parsed per-run Function. Clears its flag when deferral is not active."""
        if not function.defer_loading:
            return
        if not self.active:
            function.defer_loading = None
            model_id = getattr(self._model, "id", None)
            if self.config is not None and model_id not in _warned_models:
                _warned_models.add(model_id)
                log_warning(f"Model {model_id} does not support tool search; deferred tools are loaded normally.")
            return
        key = id(toolkit) if toolkit is not None else 0
        group = self._groups.get(key)
        if group is None:
            if toolkit is not None:
                group = _Group(name=toolkit.name, summary=summarize(toolkit.get_tool_search_summary()))
            else:
                group = _Group(name=_STANDALONE_GROUP)
            self._groups[key] = group
        group.tool_names.append(function.name)
        # Providers that group deferred tools (OpenAI namespaces) group them by toolkit
        if toolkit is not None:
            function._tool_search_group = (key, group.name, group.summary)

    def get_system_prompt_snippet(self) -> Optional[str]:
        """The searchable-tools index, or None when nothing is deferred.

        Sorted, so it changes only when the deferred tools change and keeps the prompt cache warm.
        """
        if not self._groups or not self.active or self.config is None or self.config.index == "none":
            return None

        lines = [
            "<searchable_tools>",
            "Some of your tools are not loaded yet. Find them with the tool search tool, which loads their "
            "full definitions:",
            "- Search for a tool and let it load before calling it.",
            "- Call the tools you already have directly; search only for capabilities you are missing.",
            "- If a search finds nothing, try other keywords before concluding you cannot do something.",
            "",
            "Tools you can search for:",
        ]
        groups = sorted(self._groups.values(), key=lambda g: (g.name, g.summary or "", sorted(g.tool_names)))
        for group in groups:
            name = escape_markup(group.name)
            tool_names = [escape_markup(tool_name) for tool_name in sorted(group.tool_names)]
            count = f"{len(tool_names)} tool{'s' if len(tool_names) != 1 else ''}"
            if group.summary and self.config.index == "toolkits":
                lines.append(f"- {name} ({count}): {group.summary}")
            elif group.summary:
                lines.append(f"- {name} ({count}): {group.summary} Tools: {', '.join(tool_names)}")
            else:
                lines.append(f"- {name} ({count}): {', '.join(tool_names)}")
        lines.append("</searchable_tools>")
        return "\n".join(lines)


def has_deferred_tools(tools: Optional[List[Any]]) -> bool:
    """True if any formatted provider tool dict is marked defer_loading."""
    return any(isinstance(t, dict) and t.get("defer_loading") for t in tools or [])
