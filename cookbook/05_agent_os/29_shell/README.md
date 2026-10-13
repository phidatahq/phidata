# AgentOS shell

The shell is the conversational entry point to an AgentOS: the team you talk
to in order to build and run components, inspect operations, diagnose the
deployment and read its source. The framework builds it; the application
chooses the name, the model and the resources it attaches.

```python
agent_os = AgentOS(db=db, registry=registry, shell=ShellConfig(name="Agno", model=model))
```

`shell=True` takes the registry's first model. The result is one team with id
`agno` (configurable) and members with fixed ids: `platform-builder`,
`platform-manager` and, when a workspace is configured, `platform-engineer`.
All four are served as ordinary components, so the UI, REST, MCP, interfaces
and scopes work unchanged. They never enter the registry: a component built by
Platform Builder cannot acquire the shell's toolkits.

## Files

| File | What it teaches |
|---|---|
| `basic_shell.py` | Serve an OS with its shell and a small build palette. |
| `shell_diagnostics.py` | Construct a shell and run the model-free diagnostics. No model calls. |
| `shell_with_resources.py` | Attach a notebook, knowledge, learning and the source to the shell. |

## Prerequisites

```bash
./scripts/demo_setup.sh
export OPENAI_API_KEY=...
```

## Run

```bash
.venvs/demo/bin/python cookbook/05_agent_os/29_shell/shell_diagnostics.py
.venvs/demo/bin/python cookbook/05_agent_os/29_shell/basic_shell.py
```

Then open the AgentOS UI, pick the Agno team and ask what it can build.

## Source access and build boundaries

A workspace path gives Platform Engineer read-only file tools. A supplied
`WorkspaceContextProvider` is copied into tools mode with the default exclusions
retained; additional exclusions can narrow access. `allow_paths` and custom
`!` exemptions are rejected because they could expose credential files. The
provider's model, prompt and custom tool implementations are not adopted.

Shell components remain ordinary served agents and a team, including when using
MCP or an interface. Studio cannot compose them through explicit include lists
or a second registry. Resources attached only to the lead stay outside the build
palette; declare shared knowledge on `Registry(knowledge=[...])` explicitly.

The shell reserves its team id and all three member ids, even when no workspace
is configured. Choose different ids for application components. The lead can
run itself once for a fresh context; a second nested dispatch is refused.
