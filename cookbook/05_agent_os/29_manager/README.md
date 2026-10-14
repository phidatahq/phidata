# AgentOS manager

The manager is the conversational entry point to an AgentOS: the team you talk
to in order to build and run components, inspect operations, diagnose the
deployment and read its source. The framework builds it; the application
chooses the name, the model and the resources it attaches.

```python
from agno.os import AgentOS, ManagerConfig

agent_os = AgentOS(db=db, registry=registry, manager=ManagerConfig(name="Agno", model=model))
```

`manager=True` takes the registry's first model. The result is one team with id
`agno` (configurable) and members with fixed ids: `platform-builder`,
`platform-manager` and, when a workspace is configured, `platform-engineer`.
All four are served as ordinary components, so the UI, REST, MCP, interfaces
and scopes work unchanged. They never enter the registry: a component built by
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

Then open the AgentOS UI, pick the Agno team and ask what it can build.

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

The manager needs a synchronous OS database for Studio catalog operations.
Both synchronous and asynchronous Team runs are supported. Missing models or
incompatible databases fail at construction with an actionable message.

## Migration from the unreleased shell API

Use `ManagerConfig` from `agno.os`, pass `manager=` to `AgentOS`, and replace
`agent_os.shell.team` with `agent_os.manager`. The default team id is still
`agno`, so runs continue at `/teams/agno/runs` with scope `teams:agno:run`.
The old `shell=` keyword and `ShellConfig` import are not retained as aliases.
Optional source access remains `ManagerConfig(workspace=...)`; a broader
OS `root` API and Products/Projects are separate design work.
