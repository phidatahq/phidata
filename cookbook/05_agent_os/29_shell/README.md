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
