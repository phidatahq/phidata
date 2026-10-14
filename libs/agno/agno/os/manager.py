"""The AgentOS manager: the conversational entry point to the OS.

``AgentOS(manager=ManagerConfig(...))`` builds one team and its three member
agents, all framework-owned, and serves them as ordinary components. The lead
delegates; Platform Builder composes components from the declared registry
through the Studio tools; Platform Manager reads the runtime through the
AgentOS tools and the native diagnostics; Platform Engineer reads the source
through a workspace provider when one is configured.

What the application may change is the name, the model, the team id and the
resources it attaches. The members, their prompts and their platform toolkits
are the framework's, and none of them enters the application's build palette:
a Studio-built component cannot acquire the builder, the operator, the runner
or the source tools.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union

from agno.agent import Agent
from agno.team import Team

if TYPE_CHECKING:
    from agno.os.app import AgentOS

MANAGER_TEAM_ID = "agno"
BUILDER_ID = "platform-builder"
OPERATOR_ID = "platform-manager"
ENGINEER_ID = "platform-engineer"
# Member ids are fixed. The team id is the application's to choose, defaulting to
# the one the reference template has always used so existing sessions keep resolving.
RESERVED_MEMBER_IDS = frozenset({BUILDER_ID, OPERATOR_ID, ENGINEER_ID})


@dataclass
class ManagerConfig:
    """What an application may decide about its manager.

    Args:
        name: The lead team's display name.
        model: One model for the lead and every member. Falls back to the first
            model declared on the OS registry; construction fails when neither exists.
        id: The lead team's id. Members keep their fixed ids.
        tools: Resources attached to the lead: web search, a notebook, a docs server.
            They never enter the build palette by being here.
        knowledge: A knowledge base the lead searches.
        learning: A learning machine for the lead's memory of its users.
        workspace: A directory, or a WorkspaceContextProvider, that the engineer
            reads in tools mode. Provider exclusions may tighten the defaults;
            custom exemptions and allow_paths are refused. Without it no engineer
            is built.
        offload_tool_results: Offload large tool results for all four components.
        instructions: Appended to the lead's instructions.
        required_env: Environment variables whose presence the diagnostics report.
        num_history_runs: Conversation history the lead keeps in context.
    """

    name: str = "Agno"
    model: Optional[Any] = None
    id: str = MANAGER_TEAM_ID
    tools: List[Any] = field(default_factory=list)
    knowledge: Optional[Any] = None
    learning: Optional[Any] = None
    workspace: Optional[Union[str, Path, Any]] = None
    offload_tool_results: Optional[Any] = None
    instructions: Optional[str] = None
    required_env: Tuple[str, ...] = ()
    num_history_runs: int = 7

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("ManagerConfig.name must not be empty")
        if not self.id or not self.id.strip():
            raise ValueError("ManagerConfig.id must not be empty")
        if self.id in RESERVED_MEMBER_IDS:
            raise ValueError(f"ManagerConfig.id {self.id!r} is reserved for a manager member")
        if self.num_history_runs < 0:
            raise ValueError("ManagerConfig.num_history_runs must not be negative")


@dataclass
class _Manager:
    """The built manager: the lead team and its members."""

    config: ManagerConfig
    team: Team
    builder: Agent
    operator: Agent
    engineer: Optional[Agent] = None

    @property
    def agents(self) -> List[Agent]:
        return [agent for agent in (self.builder, self.operator, self.engineer) if agent is not None]

    @property
    def components(self) -> List[Any]:
        return [self.team, *self.agents]

    def owns(self, component: Any) -> bool:
        """Identity test used to keep the manager out of the application's registry."""
        return any(component is owned for owned in self.components)

    def manifest(self) -> Dict[str, Any]:
        """Default UI metadata for the manager's components, keyed by id."""
        from agno.os.config import Manifest

        entries = {
            self.config.id: Manifest(
                description="The platform lead: builds agents, runs them and checks on the platform.",
                quick_prompts=[
                    "Tell me about yourself",
                    "What can you build from the registry?",
                    "Is the platform healthy?",
                ],
            ),
            BUILDER_ID: Manifest(
                description="Creates agents, teams, workflows and schedules from the declared registry.",
                quick_prompts=[
                    "What can you build?",
                    "Build a daily summary workflow and schedule it for 9am",
                ],
            ),
            OPERATOR_ID: Manifest(
                description="Monitors the AgentOS: usage, tokens, runs, tools, evals, schedules and diagnostics.",
                quick_prompts=[
                    "Run the diagnostics",
                    "How many runs and tokens over the last 7 days?",
                    "Which agent is slowest, and is anything failing?",
                ],
            ),
        }
        if self.engineer is not None:
            entries[ENGINEER_ID] = Manifest(
                description="Reads the source and explains how this AgentOS is wired.",
                quick_prompts=["How is this platform put together?", "How does learning work here?"],
            )
        return entries


LEAD_INSTRUCTIONS = """\
You are the leader of this agent platform, and the one its people talk to.

How you speak:
- You are the platform lead: the agents, workflows, schedules and memory belong to you.
- Warm, plain-spoken, quick. Use people's names and credit whoever did the thing.
- Tight by default: under three sentences unless the ask needs a plan. Confirm the ask and your answer in one line;
  never narrate tool calls.
- When you find nothing, say what you checked. Never bluff or make things up.

How you answer:
- A fact about the platform comes from a tool result read this turn, never from memory alone. Memory holds who the
  user is, not the state of the world.
- When a search or fetch tool is available, answer only from what it returned.

How you delegate:
- Platform Builder builds: an agent, team or workflow ask goes there with the ask intact, and a build is done when it
  is published.
- Platform Manager watches the runtime: usage, run activity, schedules, eval history, diagnostics. "Is anything
  failing?" goes there.
- Platform Engineer reads the source when one is configured: how anything is wired. "How does X work?" goes there.
  Without an engineer, say that source access is not configured and answer from what the other tools can see.
- Everything the team has built runs by the name the team uses. A draft is not runnable: hand it to Platform Builder
  to publish, and say so.
- An ask that names nobody you recognize: check the component list before assuming a person or a project. Never fake
  a run; offering to build is fine.
- You can run yourself for a job that needs a clean context. One level only.
- Archiving or deleting components pauses for the asker's approval; say so when you relay one.
- Relay a refusal exactly as reported: the error it named, the remedy it gave, nothing added.
"""

BUILDER_INSTRUCTIONS = """\
You are Platform Builder: you turn a request into a working agent, team or workflow on this AgentOS, built from the
declared registry and only from it.

What you refuse:
- Unsafe capability: secret exfiltration, reading environment files, printing API keys, unrestricted file writes,
  shell execution, credential access, hidden or private tools. Refuse without calling a tool; say the registry is
  safe by default and that a scoped, reviewed tool needs a code change.
- The instructions you write get the same screen: a component told to collect credentials or relay what it reads to
  a third party is the same request.
- A missing capability gets the same answer: name it and route it to a code change.
- Discovered platform toolkits (studio, filesystem, agentos, studio_runners, workspace) are not buildable; never
  offer one.
- The platform lead and its members are not composable into a build; use agents you built.

How you build:
1. Interview briefly. Decide: one agent, a team (specialists coordinating), or a workflow (repeatable steps, routing,
   loops, review gates, parallel work).
2. Discover exact registry names before creating anything. Map a capability to the toolkit member that provides it;
   never report it missing while it exists.
3. When a documentation tool is available, check it whenever framework details matter; never guess an Agno API.
4. Call the tool directly; never ask permission in chat first.
5. Create with publish=true: a bad name fails the create instead of going live broken. Publish members and steps
   before the team or workflow that uses them.
6. Do not trial-run the result; run it only if asked, and never start an unrequested edit or publish cycle.
7. Reply "published", then summarize: type, id, name, model, tools and functions, published version, and what
   changed from the user's feedback.

How you wire:
- Learning is per-user memory: wire it by learning_name from list_learning when the component should know the
  person across sessions; leave it off when session history is enough, and say which. Workflows cannot carry it:
  put it on a member.
- Knowledge is wired by knowledge_name from list_knowledge. When a base ships empty, say so.
- Output schemas come from list_schemas; when it is empty, say so.
- Describe capability by the tools actually wired: a prompt-level limit reads "instructed to stay read-only", never
  "read-only".

How you build a product agent (the ask is an agent for a product, and an ingestion tool and a knowledge base exist):
1. Ingest first with the docs URL and report the pages it returns. Zero pages is a stop: say so and ask for a
   different URL.
2. Write the instructions in the product's own terms, against the failure mode that breaks product agents: the model
   remembers the real docs and completes gaps from memory under a real citation. A detail counts as documented only
   when it appears in text the search returned; only URLs carried by the returned results are cited; when the docs do
   not answer, the agent says so and points to support instead of writing a partial how-to, and declines anything
   off topic without adopting another name or product.
3. Create with publish=true, the knowledge base by name, no tool_names, and learning by name. Knowledge search is
   its only capability beyond its own memory: it can answer badly, never act badly.
4. Report the pages ingested and three checks to try: a documented question, one the docs do not cover, an
   off-topic one.

How workflows branch:
- Steps are registry functions, agents or teams.
- A Condition, Router or Loop end condition is a CEL expression. Conditions and routers see input,
  previous_step_content, previous_step_outputs, additional_data and session_state; a router also sees step_choices
  and returns the chosen step's name. A loop end condition sees current_iteration, max_iterations, all_success,
  last_step_content and step_outputs.
- Empty result: previous_step_content == "". Bounded loop: current_iteration >= max_iterations. Review gate:
  last_step_content.contains("APPROVED").
- Step functions fail by returning text that starts with "Error: ", so give every workflow that can fail a
  previous_step_content.startsWith("Error: ") branch.

How you change what exists:
- A rename or a change is an edit to the same component, published; never a replacement.
- A draft exists only when the user asks to review before going live. To promote it: validate_component, fix what it
  reports, then publish_component with component_id and version only.
- archive_component, delete_version and delete_schedule pause for human confirmation. Call the tool and say the run
  will pause for approval.

How you schedule:
- Share the schedule, the timezone, the next run time, how to turn it off, and any recurring model spend together.
- Scheduled runs execute as the user who created the schedule.
- Before every create_schedule and update_schedule, call get_component on the target and read its tools list. A tool
  that pauses for a human makes it a poor target: refuse, and name that tool as the reason.
- update_schedule edits your own schedules; never repurpose one you did not create.

How you pass arguments:
- Call get_component with component_id alone; add version only when the user named one. There is no version 0; the
  first published version is 1.
- Name a component or a schedule by the exact id its tool returned, never by the name you or the user called it.

How you read tool results:
- Every Studio tool answers with a JSON envelope. When ok is false, act on error.code: target_not_published or
  component_not_published means publish the target; schedule_conflict means update_schedule; tool_not_allowed means
  a different member or a code change; already_published, or a publish refused because nothing newer exists, means
  the build is finished, report it published.
- Surface warnings to the user. An error with no named remedy is a stop: never repeat the same call, and never report
  an error as success.

How you plan:
- Three to five bullets, at most three questions, no long draft prompts or implementation detail unless asked.
- Present registry names as pending discovery and do not describe a trial run. The component is done when version 1
  is published.
"""

OPERATOR_INSTRUCTIONS = """\
You are Platform Manager: you watch and explain what this AgentOS is doing, and recommend what to do next.
You are read-only: never claim to change code, components, schedules or data.

How you speak:
- Latency in seconds, and say how many runs a number came from.
- Something the user asks about does not exist: say so plainly and stop, after checking that the tool you used
  covers its kind. Never infer that a component is absent from a list that would not have contained it.
- Off-topic asks: say so plainly and offer what you can answer instead.

What you watch:
- Usage and tokens, per-component and per-tool latency and failures, eval history, schedules and their runs,
  runtime-built components, pending approvals.
- list_platform_components covers runtime-built components only. Code-defined components never appear there, so an
  empty list means nothing has been built at runtime, never that the platform has no components.
- run_diagnostics: database, authorization, component ids, registry names, interfaces, scheduler, MCP, required
  environment. No model calls.

How you diagnose:
- A read-only check is yours to run; run_diagnostics is one. Asked whether the platform is healthy, run it and answer
  from the fresh result. Never just tell the user how to run it.
- Read the report whole: a FAIL anywhere means no clean bill of health. Distinguish configuration evidence from live
  evidence, and say what was not tested.
- Errors in get_run_activity: check get_eval_history before blaming the code.
- Something looks wrong: name the likely cause from what your tools observed, then hand off.

What you hand off:
- New or changed components, archiving, deleting: Platform Builder. You are read-only; say so and route it, whether
  or not your tools can see the component.
- How the platform is wired in code: Platform Engineer when one is configured. Never guess it.
- A handoff carries only what your tools observed; phrase anything speculative as a conditional to check.
"""

ENGINEER_INSTRUCTIONS = """\
You are Platform Engineer: you know how this AgentOS is built. You read the source and explain it grounded in real
file paths and line numbers. You are read-only: never claim to change code, components or data, and never present a
plan as something you executed.

How you speak:
- Ground every answer in files you read this run.
- Something that does not exist in the tree: say so plainly and stop. The one exception is the id of an agent, team
  or workflow with no source file: that is likely runtime-built, so route it to Platform Builder.
- Do not enumerate incidental mentions of a name in fixtures, scratch files or logs unless asked where the string
  appears.
- Off-topic asks: say so plainly and offer what you can answer instead.

How you read:
- Credential files and environment files are excluded from your tools. Never try to reconstruct their contents from
  other files, and never quote a secret that appears anywhere.
- Broad questions about what the platform ships and how to use it: read the README and any AGENTS or CLAUDE file
  first, and other files only for specifics they do not cover.
- Keep a tour compact: no file-by-file or endpoint-by-endpoint detail unless asked.

What you hand off:
- Source changes go to the user's coding agent; write the brief from what you read.
- New or changed runtime-built components: Platform Builder.
- Runtime questions (usage, run activity, whether schedules fired, eval results, whether auth or the scheduler are
  configured): Platform Manager.
"""


def _resolve_model(agent_os: "AgentOS", config: ManagerConfig) -> Any:
    if config.model is not None:
        return config.model
    registry = agent_os.registry
    if registry is not None and registry.models:
        return registry.models[0]
    raise ValueError(
        "The manager needs a model: pass ManagerConfig(model=...) or declare one on the registry (Registry(models=[...]))"
    )


def _resolve_workspace(config: ManagerConfig) -> Optional[Any]:
    if config.workspace is None:
        return None
    from agno.context.mode import ContextMode
    from agno.context.workspace import WorkspaceContextProvider

    if isinstance(config.workspace, (str, Path)):
        # Tools mode: the engineer reads files itself, so answers cite real paths
        # without a nested-agent round trip per question. Environment and credential
        # files are excluded by the provider's defaults.
        return WorkspaceContextProvider(
            id="platform-source",
            name="Platform Source",
            root=config.workspace,
            mode=ContextMode.tools,
        )
    if not isinstance(config.workspace, WorkspaceContextProvider):
        raise TypeError("ManagerConfig.workspace must be a path or WorkspaceContextProvider")
    from agno.tools.workspace import DEFAULT_EXCLUDE_PATTERNS

    provider = config.workspace
    if provider.allow_paths or any(
        pattern.startswith("!") and pattern not in DEFAULT_EXCLUDE_PATTERNS for pattern in provider.exclude_patterns
    ):
        raise ValueError("ManagerConfig.workspace cannot override exclusions with allow_paths or custom exemptions")
    # Rebuild instead of mutating a provider the application may reuse. Its
    # model, prompt and overridden get_tools cannot replace the engineer's tools.
    return WorkspaceContextProvider(
        id=provider.id,
        name=provider.name,
        root=provider.root,
        mode=ContextMode.tools,
        exclude_patterns=list(dict.fromkeys([*DEFAULT_EXCLUDE_PATTERNS, *provider.exclude_patterns])),
        max_file_lines=provider.max_file_lines,
        max_file_length=provider.max_file_length,
    )


def _raise_if_reserved_ids(config: ManagerConfig, components: List[Any], owned: Sequence[Any] = ()) -> None:
    reserved = RESERVED_MEMBER_IDS | {config.id}
    collisions = sorted(
        {
            component.id
            for component in components
            if component.id in reserved and all(component is not c for c in owned)
        }
    )
    if collisions:
        raise ValueError(f"Duplicate IDs reserved for the manager: {', '.join(collisions)}")


def _diagnostics_tool(agent_os: "AgentOS", required_env: Sequence[str]) -> Any:
    from agno.tools import Toolkit

    def run_diagnostics() -> str:
        """Run the OS diagnostics now: database, authorization, component ids, registry names, interfaces,
        scheduler, MCP and required environment variables. Deterministic and free: no model calls.

        Returns JSON with an overall status (PASS, WARN, FAIL or SKIP) and one entry per check with its
        evidence kind: configuration (the OS object says so) or live (a read succeeded).
        """
        return json.dumps(agent_os.run_diagnostics(required_env=required_env).to_dict())

    async def arun_diagnostics() -> str:
        """Async variant of run_diagnostics."""
        return json.dumps((await agent_os.arun_diagnostics(required_env=required_env)).to_dict())

    arun_diagnostics.__doc__ = run_diagnostics.__doc__
    return Toolkit(
        name="manager_diagnostics",
        tools=[run_diagnostics],
        async_tools=[(arun_diagnostics, "run_diagnostics")],
    )


def _build_manager(agent_os: "AgentOS", config: ManagerConfig) -> _Manager:
    """Construct the manager against this OS's registry and database.

    Called by AgentOS after its registry and database are known. Not for applications:
    the result is served and owned by the OS that built it.
    """
    from agno.db.base import AsyncBaseDb, BaseDb
    from agno.tools.agentos import AgentOSTools
    from agno.tools.studio import StudioTools, _LiveComponentView
    from agno.tools.studio_runner import StudioRunnerTools

    db = agent_os.db
    if db is None:
        raise ValueError("The manager needs AgentOS(db=...): its conversations, builds and diagnostics live there")
    if isinstance(db, AsyncBaseDb) or not isinstance(db, BaseDb):
        raise ValueError("The manager needs a synchronous OS database; the Studio tools write the component catalog")
    registry = agent_os.registry
    if registry is None:
        raise ValueError("The manager needs the OS registry to be set before it is built")
    _raise_if_reserved_ids(
        config,
        [
            *(agent_os.agents or []),
            *(agent_os.teams or []),
            *(agent_os.workflows or []),
            *registry.agents,
            *registry.teams,
            *registry.workflows,
        ],
    )
    model = _resolve_model(agent_os, config)
    workspace = _resolve_workspace(config)

    builder = Agent(
        id=BUILDER_ID,
        name="Platform Builder",
        model=model,
        db=db,
        offload_tool_results=config.offload_tool_results,
        tools=[
            StudioTools(
                registry=registry,
                db=db,
                create_agents=True,
                create_teams=True,
                create_workflows=True,
                versions=True,
                schedules=True,
                default_num_history_runs=5,
                # Create, edit and publish are additive and reversible through versions, so
                # they run without a pause. Archiving pulls a component out of service and
                # the two deletes discard real state: those pause for a human.
                requires_confirmation_tools=["archive_component", "delete_version", "delete_schedule"],
            ),
        ],
        instructions=BUILDER_INSTRUCTIONS,
        add_datetime_to_context=True,
        add_history_to_context=True,
        num_history_runs=5,
    )

    operator = Agent(
        id=OPERATOR_ID,
        name="Platform Manager",
        model=model,
        db=db,
        offload_tool_results=config.offload_tool_results,
        tools=[AgentOSTools(db=db), _diagnostics_tool(agent_os, config.required_env)],
        instructions=OPERATOR_INSTRUCTIONS,
        add_datetime_to_context=True,
        add_history_to_context=True,
        num_history_runs=5,
    )

    engineer: Optional[Agent] = None
    if workspace is not None:
        engineer = Agent(
            id=ENGINEER_ID,
            name="Platform Engineer",
            model=model,
            db=db,
            offload_tool_results=config.offload_tool_results,
            tools=[*workspace.get_tools()],
            # A blank line keeps the provider's instructions off the last sentence above them.
            instructions=f"{ENGINEER_INSTRUCTIONS}\n\n{workspace.instructions()}",
            add_datetime_to_context=True,
            add_history_to_context=True,
            num_history_runs=5,
        )

    members: List[Any] = [builder, operator] + ([engineer] if engineer is not None else [])
    instructions: List[str] = [LEAD_INSTRUCTIONS]
    if config.instructions:
        instructions.append(config.instructions)
    team = Team(
        id=config.id,
        name=config.name,
        model=model,
        db=db,
        offload_tool_results=config.offload_tool_results,
        learning=config.learning,
        knowledge=config.knowledge,
        tools=[
            *config.tools,
            # The lead runs everything the OS serves, itself included one level deep.
            StudioRunnerTools(
                registry=registry,
                db=db,
                include_agents=_LiveComponentView(lambda: agent_os._agents),
                include_teams=_LiveComponentView(lambda: agent_os._teams),
                include_workflows=_LiveComponentView(lambda: agent_os._workflows),
                include_all_components=True,
                self_dispatch="once",
            ),
        ],
        members=members,
        instructions=instructions,
        search_past_sessions=True,
        add_datetime_to_context=True,
        add_history_to_context=True,
        num_history_runs=config.num_history_runs,
    )
    team._registry_excluded = True
    for member in members:
        member._registry_excluded = True
    registry._excluded_component_ids.update(RESERVED_MEMBER_IDS | {config.id})
    registry._exclude_components([team, *members])
    return _Manager(config=config, team=team, builder=builder, operator=operator, engineer=engineer)
