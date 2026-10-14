# AgentOS manager

The manager is the conversational entry point to an AgentOS: the team you talk
to in order to build and run components, inspect operations, diagnose the
deployment and read its source. The framework builds it; the application
chooses the name, the model and the resources it attaches.

```python
from agno.os import AgentOS, ManagerConfig

agent_os = AgentOS(db=db, registry=registry, manager=ManagerConfig(model=model))
```

`manager=True` takes the registry's first model. The result is one team, OS
Manager, with id `os-manager`, and members with fixed ids: `platform-builder`,
`platform-manager` and, when a workspace is configured, `platform-engineer`.
`ManagerConfig(name=..., id=...)` renames the team; the member ids stay fixed.
The team and its members are served as ordinary components, so the UI, REST,
MCP, interfaces and scopes work unchanged. They never enter the registry: a component built by
Platform Builder cannot acquire the manager's toolkits.

## Files

| File | What it teaches |
|---|---|
| `basic_manager.py` | Serve an OS with its manager and a small build palette. |
| `manager_diagnostics.py` | Construct a manager and run the model-free diagnostics. No model calls. |
| `manager_with_resources.py` | Attach a notebook, knowledge, learning and the source to the manager. |

## Prerequisites

```bash
./scripts/demo_setup.sh
export OPENAI_API_KEY=...
```

## Run

```bash
.venvs/demo/bin/python cookbook/05_agent_os/29_manager/manager_diagnostics.py
.venvs/demo/bin/python cookbook/05_agent_os/29_manager/basic_manager.py
```

Then open the AgentOS UI, pick the OS Manager team and ask what it can build.

## Source access and build boundaries

A workspace path gives Platform Engineer read-only file tools. A supplied
`WorkspaceContextProvider` is copied into tools mode with the default exclusions
retained; additional exclusions can narrow access. `allow_paths` and custom
`!` exemptions are rejected because they could expose credential files. The
provider's model, prompt and custom tool implementations are not adopted.

Manager components remain ordinary served agents and a team, including when using
MCP or an interface. Studio cannot compose them through explicit include lists
or a second registry. Resources attached only to the lead stay outside the build
palette; declare shared knowledge on `Registry(knowledge=[...])` explicitly.

The manager reserves its team id and all three member ids, even when no workspace
is configured. Choose different ids for application components. The lead can
run itself once for a fresh context; a second nested dispatch is refused.

## Direct use

`agent_os.manager` is the actual served `Team`; it is `None` when disabled.
Use the ordinary Team methods and members:

```python
result = agent_os.manager.run("Check the platform", user_id="alice")
result = await agent_os.manager.arun("Check the platform", user_id="alice")
members = agent_os.manager.members
```

## Interfaces and MCP

The manager exists once `AgentOS` is constructed, and interfaces and the MCP
server are mounted by `get_app()`. Bind them in between:

```python
agent_os = AgentOS(db=db, registry=registry, manager=ManagerConfig(model=model), mcp=True)
agent_os.interfaces.append(Slack(team=agent_os.manager, token=token, signing_secret=secret))
agent_os.mcp = MCPConfig(default_tools=True, tools=[agent_os.manager.as_tool(name="os_manager")])
app = agent_os.get_app()
```

The manager needs a synchronous OS database for Studio catalog operations.
Both synchronous and asynchronous Team runs are supported. Missing models or
incompatible databases fail at construction with an actionable message.

## Diagnostics

`agent_os.run_diagnostics()` and `await agent_os.arun_diagnostics()` make no model
calls. SQL diagnostics probe the connection before reading sessions, including
when the database has no tables yet. Scheduler checks scan up to 10,000 enabled
schedules and report WARN if the scan is incomplete or an overdue schedule is found.

To probe MCP, pass `network_probe=True, public_url="https://your-os.example"`.
Use the OS base URL, including any proxy path prefix; the probe appends the
configured MCP path or uses `/` on the configured MCP root host.
