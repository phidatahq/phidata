# AgentOS manager

Add an OS manager to build and run agents, teams and workflows through chat.
It can also check platform activity, run diagnostics and read source code.
Choose its name, model and resources with `ManagerConfig`.

```python
from agno.os import AgentOS, ManagerConfig

agent_os = AgentOS(db=db, registry=registry, manager=ManagerConfig(model=model))
```

Use `manager=True` to use the registry's first model. The manager is a Team named
OS Manager, with id `os-manager`. It has these members:

- **Platform Builder** (`platform-builder`): creates components using the registry.
- **Platform Manager** (`platform-manager`): checks activity and runs diagnostics.
- **Platform Engineer** (`platform-engineer`): reads source when a workspace is configured.

Set `ManagerConfig(name=..., id=...)` to change the team's name and id. Member ids
are fixed. Use the team and its members through the usual UI, REST, MCP and
interfaces, with the usual scopes. They are excluded from the registry, so
Platform Builder cannot add their tools to new components.

## Files

| File | What it teaches |
|---|---|
| `basic_manager.py` | Serve an AgentOS with an OS manager. |
| `manager_diagnostics.py` | Run diagnostics without model calls. |
| `manager_with_resources.py` | Add a notebook, knowledge, learning and source access. |

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

## Source access and the registry

A workspace path gives Platform Engineer read-only file tools. You can also pass
a `WorkspaceContextProvider`. Its settings are copied into tools mode, keeping
the default file exclusions. You can exclude more files, but `allow_paths` and
custom `!` exemptions are rejected because they could expose credentials.
The provider's model, prompt and custom tools are not used.

Studio cannot add manager components to new builds, even through include lists
or another registry. Resources added only to the manager are not available to
Platform Builder. To share a knowledge base, add it to `Registry(knowledge=[...])`.

The manager reserves its team id and all three member ids, even when no workspace
is configured. Use different ids for your own components. The manager can run
itself once with a fresh context. It cannot start another self-run from that run.

## Direct use

`agent_os.manager` is the manager Team, or `None` when disabled.
Use its Team methods and members directly:

```python
result = agent_os.manager.run("Check the platform", user_id="alice")
result = await agent_os.manager.arun("Check the platform", user_id="alice")
members = agent_os.manager.members
```

## Interfaces and MCP

Create `AgentOS`, then connect the manager to interfaces or MCP before calling
`get_app()`:

```python
agent_os = AgentOS(db=db, registry=registry, manager=ManagerConfig(model=model), mcp=True)
agent_os.interfaces.append(Slack(team=agent_os.manager, token=token, signing_secret=secret))
agent_os.mcp = MCPConfig(default_tools=True, tools=[agent_os.manager.as_tool(name="os_manager")])
app = agent_os.get_app()
```

The manager needs a synchronous database because Studio uses it to save
components. Both sync and async Team runs are supported. Creating the OS raises
an error if the model is missing or the database type is unsupported.

## Diagnostics

`agent_os.run_diagnostics()` and `await agent_os.arun_diagnostics()` make no model
calls. SQL diagnostics probe the connection before reading sessions, including
when the database has no tables yet. Scheduler checks scan up to 10,000 enabled
schedules and report WARN if the scan is incomplete or an overdue schedule is found.

To probe MCP, pass `network_probe=True, public_url="https://your-os.example"`.
Use the OS base URL, including any proxy path prefix; the probe appends the
configured MCP path or uses `/` on the configured MCP root host.
