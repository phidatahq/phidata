# OS Manager

OS Manager is a team you talk to through AgentOS. It can check activity, run
diagnostics, run existing components and ask its members to build new ones.
Start with a model and a database:

```python
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, ManagerConfig

agent_os = AgentOS(
    db=SqliteDb(db_file="tmp/manager.db"),
    manager=ManagerConfig(model=OpenAIResponses(id="gpt-5.6-luna")),
)
```

## Try the examples

From the repository root, set up the environment:

```bash
./scripts/demo_setup.sh
```

Start with diagnostics. This makes no model calls and does not need an API key:

```bash
.venvs/demo/bin/python cookbook/05_agent_os/29_manager/manager_diagnostics.py
```

Expect a JSON report. A missing `OPENAI_API_KEY` produces FAIL because the example
lists it as required. Disabled authorization produces WARN. These results show
what needs configuring; running the script itself does not require either.

For a conversation, set your API key and start one of the serving examples:

```bash
export OPENAI_API_KEY=...
.venvs/demo/bin/python cookbook/05_agent_os/29_manager/basic_manager.py
```

Connect the AgentOS UI to `http://localhost:7777` and select the **OS Manager**
team. Stop the server before starting another example on the same port.
Conversations use the configured model and incur provider charges.

| File | Ask OS Manager | What to expect |
|---|---|---|
| `basic_manager.py` | “Run diagnostics and explain any issues.” | A report from Platform Manager, including the authorization warning. No tools or models have been supplied for building new agents. |
| `manager_user_access.py` | As Alice, ask “Run math-helper: what is 6 * 7?” Then ask to publish a new agent. | The permitted run succeeds; publishing is refused. Configure `JWT_VERIFICATION_KEY` and a JWT with `sub=alice`, `aud=manager-access-demo`. |
| `manager_builds_agents.py` | “Create a calculator agent named Budget Helper.” Then: “Run Budget Helper: what is 15% of 240?” | Platform Builder publishes the agent. The second request runs it and should return 36. |
| `manager_with_resources.py` | “Save a note in project.md: the demo is on Friday.” Then: “Read project.md.” | The shared notebook stores and retrieves the note. |
| `manager_with_resources.py` | “Remember that I prefer short answers.” Then ask about your preference in a new session with the same user id. | The manager can save and retrieve a user preference across sessions. |
| `manager_with_resources.py` | “Read basic_manager.py and explain how the manager is configured.” | Platform Engineer reads the example from its configured workspace. |

To try the build example:

```bash
.venvs/demo/bin/python cookbook/05_agent_os/29_manager/manager_builds_agents.py
```

To try the notebook, memory and source tools:

```bash
.venvs/demo/bin/python cookbook/05_agent_os/29_manager/manager_with_resources.py
```

Each serving example uses its own SQLite file under `tmp/`, so conversations,
notes and published components persist between runs. Use PostgreSQL in production.

## When to use a registry

You do not need to configure a registry just to add a manager. Pass its model
through `ManagerConfig`, as in the basic example.

Use a `Registry` when you want to choose resources for components the builder
creates: models, tools, workflow functions, knowledge or learning. The build
example supplies a model, calculator tools and JSON/CSV functions. It uses
`manager=True` so the manager uses the first model in that registry too.

Tools passed to `ManagerConfig(tools=[...])` are for the manager itself. They do
not become tools for new agents. To share a resource with the builder, include
it in the registry as well. Code-defined application components also contribute
resources through AgentOS registry discovery. Manager components are excluded.

## The team and its members

The default team name is **OS Manager**, with id `os-manager`. Set
`ManagerConfig(name=..., id=...)` to change them. Its members are:

- **Platform Builder** (`platform-builder`): creates components and schedules.
- **Platform Manager** (`platform-manager`): checks activity and runs diagnostics.
- **Platform Engineer** (`platform-engineer`): reads source when a workspace is configured.

The team and its members use the normal UI, REST and MCP routes. Ordinary run
grants, including `teams:os-manager:run`, let a user talk to the manager. Access
to the manager does not grant its tools additional permissions:

- Running another component requires its agent, team or workflow `run` permission.
- Discovery filters components by their `read` permission. Registry discovery
  requires `registry:read`; catalog inspection requires `components:read`.
- Creating, editing and publishing components requires `components:write`.
  Archiving, restoring and deleting versions requires `components:delete`.
- Schedule tools require the corresponding `schedules:read`, `schedules:write`
  or `schedules:delete` permission. Creating or editing a schedule also checks
  permission to run its target.
- Diagnostics requires `config:read`; workspace reads require `filesystem:read`.
- Platform-wide operational aggregates remain administrator-only because these
  queries do not provide a per-user view.

These checks also apply when the protected built-in toolkits are attached to
other authenticated agents. Existing callers with only an agent's run grant need
the corresponding tool permissions; ordinary agent runs without these tools keep
their existing permission requirements.

These decisions use the configured authorization provider, including managed
roles and custom policies. JWT claims cannot override those policies. Service
accounts retain their own token ACL. Authority follows specialist delegation,
MCP calls and queued execution; a continuation uses its current caller's authority.
Permission-sensitive tools recheck access rather than serving cached results.

Schedules created or edited under authorization retain the caller's permission
snapshot. The executor uses that snapshot for the target and its tools, rather
than its internal transport credential. Managed policies are consulted when the
schedule runs. Token-scope grants are captured when the schedule is saved; edit
or delete the schedule to change them. Existing schedules without a snapshot
cannot use platform tools on an authenticated deployment; recreate or edit them
as an authorized caller.

Direct Python calls, security-key access, unauthenticated deployments and interfaces
bound directly to the team are trusted application entry points. Expose those only
to trusted operators; binding Slack does not enforce REST user roles. Custom tools
supplied through `ManagerConfig.tools` remain application-defined capabilities:
use `RunContext.authorization` or `requires_permission` from
`agno.run.authorization` when they need caller authorization.

Their ids are reserved, including the engineer id when no workspace is
configured. The manager can run itself once with a fresh context; it cannot start
another self-run from that run.

A workspace path gives the engineer read-only file tools with default exclusions
for credential files. A supplied `WorkspaceContextProvider` is copied into tools
mode. Its model, prompt and custom tools are not used. Additional exclusions are
supported; `allow_paths` and custom `!` exemptions are rejected.

The resources example shares notebook files across users, while learning keeps
user memory separate. It does not configure a knowledge base.

## Large tool results

OS Manager and its members offload tool results by default on SQLite and
PostgreSQL. Results above 16,000 characters are stored in the database; the
model receives a preview and can read or search the full result. Small results
stay inline. Other database adapters warn and leave offloading disabled.

Use `ManagerConfig(offload_tool_results=False)` to disable it, or pass a
`ResultStore` to customize the threshold and retention:

```python
from agno.offload import ResultStore

manager_config = ManagerConfig(
    model=OpenAIResponses(id="gpt-5.6-luna"),
    offload_tool_results=ResultStore(threshold_chars=32000, ttl_seconds=86400),
)
```

Pass this config as `AgentOS(db=db, manager=manager_config)`. The custom example
expires stored results after one day; the default has no time-based expiry.

## Direct use

`agent_os.manager` is a regular Team, or `None` when disabled. Use its sync or
async methods with a user id and session id:

```python
result = agent_os.manager.run("Run diagnostics", user_id="alice", session_id="review")
```

In async code:

```python
result = await agent_os.manager.arun("Run diagnostics", user_id="alice", session_id="review")
```

The manager needs a synchronous database because Studio uses it to save
components. Both sync and async Team runs are supported. Creating the OS raises
an error if the model is missing or the database type is unsupported.

To attach an interface or expose `agent_os.manager.as_tool()` through MCP, create
the OS first, configure the interface or MCP tools, then call `get_app()`.

## Diagnostics

`agent_os.run_diagnostics()` and `await agent_os.arun_diagnostics()` make no model
calls. SQL diagnostics probe the connection before reading sessions, including
when the database has no tables yet. Scheduler checks scan up to 10,000 enabled
schedules and report WARN if the scan is incomplete or an overdue schedule is found.

To probe MCP, pass `network_probe=True, public_url="https://your-os.example"`.
Use the OS base URL, including any proxy path prefix; the probe appends the
configured MCP path or uses `/` on the configured MCP root host.
