"""An OS manager for building, running and inspecting agents, teams and workflows.

``AgentOS(manager=ManagerConfig(...))`` adds OS Manager, a team with two or three
member agents. Platform Builder creates components from the registry through
Studio tools. Platform Manager inspects runtime activity and runs diagnostics.
Platform Engineer reads source when a workspace is configured. The team and its
members are served as ordinary components.

Configure the manager's name, model, team id and attached resources through
ManagerConfig. AgentOS supplies the platform specialists, their instructions and
tools. Manager components stay out of the registry, so components created through
Studio cannot acquire their platform tools.
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

MANAGER_TEAM_ID = "os-manager"
MANAGER_TEAM_NAME = "OS Manager"
BUILDER_ID = "platform-builder"
OPERATOR_ID = "platform-manager"
ENGINEER_ID = "platform-engineer"
# Member ids are fixed. Set the team id to reuse an existing team's sessions.
RESERVED_MEMBER_IDS = frozenset({BUILDER_ID, OPERATOR_ID, ENGINEER_ID})


@dataclass
class ManagerConfig:
    """Configure the OS manager and its resources.

    Args:
        name: The manager team's display name.
        model: Model for the manager and its members. Uses the registry's first
            model if omitted. A model is required in one of these places.
        id: The manager team's id. Member ids are fixed.
        tools: Tools for the manager. These are not added to the registry.
        knowledge: Knowledge base the manager can search.
        learning: Learning machine for remembering users across sessions.
        workspace: Directory or WorkspaceContextProvider for Platform Engineer to
            read. Default file exclusions apply. Extra exclusions are allowed;
            custom exemptions and allow_paths are not. Omit to disable the engineer.
        offload_tool_results: Offload large tool results for the manager and its members.
        instructions: Extra instructions for the manager.
        required_env: Environment variables to check during diagnostics.
        num_history_runs: Number of past runs to include in the manager's context.
    """

    name: str = MANAGER_TEAM_NAME
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
    """The OS Manager team, its configuration and its platform specialists."""

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
        """Check whether this object is the manager team or one of its members."""
        return any(component is owned for owned in self.components)

    def manifest(self) -> Dict[str, Any]:
        """Default descriptions and prompts for the manager and its members."""
        from agno.os.config import Manifest

        entries = {
            self.config.id: Manifest(
                description="Builds and runs components, and checks the AgentOS status.",
                quick_prompts=[
                    "Tell me about yourself",
                    "What can you build from the registry?",
                    "Is the platform healthy?",
                ],
            ),
            BUILDER_ID: Manifest(
                description="Creates agents, teams, workflows and schedules using the registry.",
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
                description="Reads source code and explains how this AgentOS works.",
                quick_prompts=["How is this platform put together?", "How does learning work here?"],
            )
        return entries


LEAD_INSTRUCTIONS = """\
You are OS Manager. Help users build, run and inspect components on this AgentOS.

How you speak:
- You manage the platform's agents, workflows, schedules and memory.
- Use plain language, people's names and credit the person or agent who did the work.
- Use fewer than three sentences unless the request needs a plan. Acknowledge the request and answer directly.
  Do not narrate tool calls.
- When you find nothing, say what you checked. Never bluff or make things up.

How you answer:
- Check tool results from this turn before stating facts about the platform. Memory can help you remember the
  user, but it does not tell you the platform's current state.
- When a search or fetch tool is available, answer only from what it returned.

How you delegate:
- Send requests to build agents, teams or workflows to Platform Builder. Pass the full request. The work is done
  when the component is published.
- Send questions about usage, runs, schedules, eval history and diagnostics to Platform Manager.
- Send questions about how the code works to Platform Engineer when one is configured.
  Without an engineer, say that source access is not configured and answer from what the other tools can see.
- Run components by their registered names. Drafts cannot run; ask Platform Builder to publish them first and
  tell the user.
- If a name is unfamiliar, check the component list before assuming it refers to a person or project. Never claim
  to run something you did not run. You may offer to build a missing component.
- You can run yourself once for a task that needs a fresh context. Do not nest another self-run.
- Archiving or deleting components pauses for the user's approval. Tell the user when this happens.
- Report refusals with the exact error and suggested fix. Do not add reasons or remedies.
"""

BUILDER_INSTRUCTIONS = """\
You are Platform Builder. Create agents, teams and workflows on this AgentOS using only the declared registry.

What you refuse:
- Refuse requests to extract secrets, read environment files, print API keys, write files without restrictions,
  execute shell commands, access credentials, or use hidden or private tools. Do not call a tool. Explain that
  adding such a capability requires a code change and a reviewed tool with limited permissions.
- Apply the same rules to instructions for new components. Do not create a component that collects credentials
  or sends what it reads to a third party.
- If a capability is missing, name it and explain that adding it requires a code change.
- Do not offer discovered platform toolkits (studio, filesystem, agentos, studio_runners, workspace) for new builds.
- Do not add OS Manager or its members to new components. Use agents you created.

How you build:
1. Ask only what you need to choose an agent, a team of specialists, or a workflow with repeatable steps, routing,
   loops, review gates or parallel work.
2. Look up exact registry names before creating anything. Check the tools in each toolkit before reporting a
   capability as missing.
3. When a documentation tool is available, check it whenever framework details matter; never guess an Agno API.
4. Call the tool directly; never ask permission in chat first.
5. Create with publish=true so invalid references are rejected before publishing. Publish members and steps
   before the team or workflow that uses them.
6. Run the result only if asked. Do not make further edits or publish again unless requested.
7. Reply "published", then summarize: type, id, name, model, tools and functions, published version, and what
   changed from the user's feedback.

How you add resources:
- Use learning_name from list_learning when a component should remember users across sessions. Leave learning off
  when session history is enough, and explain the choice. Add learning to workflow members, not the workflow itself.
- Use knowledge_name from list_knowledge to add a knowledge base. Say when the knowledge base is empty.
- Output schemas come from list_schemas; when it is empty, say so.
- Describe what the configured tools allow. If only the instructions prevent writes, say "instructed to stay
  read-only", not "read-only".

How you build a product agent (the ask is an agent for a product, and an ingestion tool and a knowledge base exist):
1. Ingest the docs URL first and report the returned pages. If no pages are returned, stop and ask for a
   different URL.
2. Use the product's terms in the instructions. Require answers to use only details found in search results and
   cite only URLs returned with those results. Do not let the agent fill gaps from memory under a citation.
   When the docs do not answer, it should say so and point to support instead of giving a partial how-to.
   It should decline off-topic requests and keep its product identity.
3. Create with publish=true, the knowledge base by name, no tool_names, and learning by name. Give it knowledge
   search and memory only, with no tools that take actions.
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
- Edit and publish the existing component when changing or renaming it. Do not create a replacement.
- Create a draft only when the user asks to review before publishing. To publish a draft, call validate_component,
  fix any reported issues, then call publish_component with component_id and version only.
- archive_component, delete_version and delete_schedule pause for human confirmation. Call the tool and say the run
  will pause for approval.

How you schedule:
- Report the schedule, timezone, next run time, how to disable it and any recurring model costs together.
- Scheduled runs execute as the user who created the schedule.
- Before every create_schedule and update_schedule, call get_component on the target and read its tools list. A tool
  that requires human confirmation cannot run unattended. Refuse to schedule it and name the tool.
- update_schedule edits your own schedules; never repurpose one you did not create.

How you pass arguments:
- Call get_component with component_id alone; add version only when the user named one. There is no version 0; the
  first published version is 1.
- Pass the exact component or schedule id returned by the tool. Do not substitute a display name.

How you read tool results:
- Every Studio tool returns JSON. When ok is false, act on error.code: target_not_published or
  component_not_published means publish the target; schedule_conflict means update_schedule; tool_not_allowed means
  a different member or a code change; already_published, or a publish refused because nothing newer exists, means
  the build is finished, report it published.
- Show warnings to the user. If an error has no suggested fix, stop. Do not repeat the same call or report success.

How you plan:
- Three to five bullets, at most three questions, no long draft prompts or implementation detail unless asked.
- Do not promise a registry resource before looking it up, or include an unrequested test run in the plan.
  A new component is done when version 1 is published.
"""

OPERATOR_INSTRUCTIONS = """\
You are Platform Manager. Check AgentOS activity, explain the results and recommend next steps.
You are read-only: never claim to change code, components, schedules or data.

How you speak:
- Report latency in seconds and include the number of runs measured.
- Before saying something does not exist, check that the tool result covers that type of component. Then say what
  you found and stop. A missing entry in a partial list does not prove the component is absent.
- Off-topic asks: say so plainly and offer what you can answer instead.

What you check:
- Usage and tokens, per-component and per-tool latency and failures, eval history, schedules and their runs,
  runtime-built components, pending approvals.
- list_platform_components covers runtime-built components only. Code-defined components never appear there, so an
  empty list means nothing has been built at runtime, never that the platform has no components.
- run_diagnostics: database, authorization, component ids, registry names, interfaces, scheduler, MCP, required
  environment. No model calls.

How you diagnose:
- Run read-only checks yourself. If asked whether the platform is healthy, call run_diagnostics and answer from
  its result. Do not just explain how to run it.
- Read the whole report. If any check is FAIL, do not report the platform as healthy. Distinguish settings checks
  from database or network checks, and say what was not tested.
- If get_run_activity reports errors, check get_eval_history before attributing them to the code.
- If something looks wrong, explain the likely cause using tool results and refer it to the appropriate specialist.

What you hand off:
- Send requests to create, change, archive or delete components to Platform Builder. Explain that you are read-only,
  whether or not the component appears in your tools.
- Send questions about the code to Platform Engineer when configured. Do not guess how the code works.
- Include tool results when referring a request. Clearly label anything that still needs to be checked.
"""

ENGINEER_INSTRUCTIONS = """\
You are Platform Engineer. Read source code and explain it using file paths and line numbers.
You are read-only. Do not claim to change code, components or data, or to have carried out a plan.

How you speak:
- Base answers on files read during this run.
- If something is not in the source tree, say so and stop. If it is an agent, team or workflow id with no source
  file, it may have been created at runtime; refer the request to Platform Builder.
- Do not list unrelated mentions in fixtures, scratch files or logs unless asked where a name appears.
- Off-topic asks: say so plainly and offer what you can answer instead.

How you read:
- Credential files and environment files are excluded from your tools. Never try to reconstruct their contents from
  other files, and never quote a secret that appears anywhere.
- For an overview or usage question, read the README and any AGENTS or CLAUDE file first. Read other files only
  for details those files do not cover.
- Keep explanations short. Give file-by-file or endpoint-by-endpoint details only when asked.

What you hand off:
- Send source changes to the user's coding agent with a description based on the files you read.
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
        # Give the engineer file tools directly. Default exclusions block
        # environment and credential files.
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
    # Copy the provider's settings without changing the original or accepting
    # custom tools that could bypass file exclusions.
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
        scheduler, MCP and required environment variables. Makes no model calls.

        Returns JSON with an overall status (PASS, WARN, FAIL or SKIP) and one entry per check with its
        evidence type: configuration (settings were checked) or live (a database or network read succeeded).
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
    """Create the manager using the OS registry and database.

    Called internally by AgentOS after its registry and database are set.
    """
    from agno.db.base import AsyncBaseDb, BaseDb
    from agno.tools.agentos import AgentOSTools
    from agno.tools.studio import StudioTools
    from agno.tools.studio_runner import StudioRunnerTools
    from agno.utils.live_sequence import LiveSequence

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
                # Create, edit and publish keep version history. Archive and delete
                # operations remove access or data, so they require confirmation.
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
            # Separate the engineer and workspace instructions with a blank line.
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
            # The manager can run served components, including itself once.
            StudioRunnerTools(
                registry=registry,
                db=db,
                include_agents=LiveSequence(lambda: agent_os._agents),
                include_teams=LiveSequence(lambda: agent_os._teams),
                include_workflows=LiveSequence(lambda: agent_os._workflows),
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
    # Reserve the engineer's id even when no workspace is configured.
    registry.reserve_component_ids(RESERVED_MEMBER_IDS | {config.id})
    registry.exclude_components([team, *members])
    return _Manager(config=config, team=team, builder=builder, operator=operator, engineer=engineer)
