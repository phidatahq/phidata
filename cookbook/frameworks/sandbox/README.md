# Sandbox execution primitives

Run commands in a customer-operated Docker environment for trusted teams. This is the compute foundation for session sandboxes. It does not yet connect Claude/Codex agents to AgentOS or provide durable session recovery.

This is different from `DockerTools`, which gives an agent tools to manage containers on the host. `DockerSandbox` gives each session its own isolated container that the agent works inside.

Install the repository development environment and Docker, then run:

```bash
docker pull python:3.12-slim
.venv/bin/python cookbook/frameworks/sandbox/docker_execution.py
```

The example creates a sandbox container, writes and reads a file, reuses that container and deletes it. No model credentials are needed. Set `AGNO_SANDBOX_IMAGE` to a trusted Linux image containing `python`; pin its digest for repeatable deployments. The Docker context on the service host selects the trusted daemon and its authentication configuration.

`DockerSandbox(image=..., memory_mb=...)` holds settings shared by every session of an agent. `create(session_id, agent_id=None, generation=1, env=None)` identifies one session and returns a `SandboxHandle`; pass that handle to `exec`, `stop` and `destroy` so a stale caller can never act on a newer container that reuses the name. `namespace` (default `"default"`) separates deployments sharing a daemon. Repeating `create` with the same identity and configuration returns a handle to the same running container, including after an uncertain creation response. A stopped generation cannot be restarted through `create`: recovery must call `create` with a new `generation`. This prevents accidentally treating lost tmpfs files as retained session state.

`DockerSandbox` offers `create/get/exec/stop/destroy` and their asynchronous `acreate/aget/aexec/astop/adestroy` counterparts. Command arguments are passed as a sequence; explicitly use `sh -c` when shell syntax is intended. Nonzero command exits are returned as `ExecResult`; infrastructure failures raise `SandboxError`. Uncertain commands are never retried automatically.

## Warm reuse between turns

```bash
.venv/bin/python cookbook/frameworks/sandbox/warm_reuse.py
```

The example does a turn's worth of work, writing a file and leaving a background process running, then pauses the container. Pausing uses the kernel freezer: files, memory and processes stay exactly as they are, no bytes are copied anywhere, and commands are refused until the container resumes. The next turn calls `resume` and gets the same container back running, with the file present and the background process continuing from where it froze; `create` on the paused generation is refused. The example then stops the container to show the cold path: the tmpfs files are gone, the generation cannot restart, and the next turn needs generation 2 restored from a checkpoint.

`pause`, `resume` and their async counterparts are part of the `Sandbox` contract. A provider without a native pause raises `NotImplementedError`, so a caller can fall back to keeping the container running or to the cold path. A paused container is still tied to one host and still counts against its memory, so pausing complements checkpoints rather than replacing them: checkpoints remain the recovery path when the host or the container is gone.

## A live Claude session in a sandbox

```bash
export ANTHROPIC_API_KEY=...   # or CLAUDE_CODE_OAUTH_TOKEN
.venv/bin/python cookbook/frameworks/sandbox/claude_runtime.py
```

The example runs two Claude turns on one session inside a container built from the runtime image, with a pause between them. Turn 1 asks Claude to write and run a program; its tool calls and content stream back through the runtime journal, the file lands in `/workspace`, and Claude Code's own session is kept under `/runtime/native` next to the local history database. The container is then paused and resumed. Turn 2 asks, without tools, what the previous turn did. Claude answers from its native session, and the example asserts the Claude session id recorded on the local session row is the same for both turns.

Only the selected model credential is forwarded into the container environment. `runtime_config` holds the `ClaudeAgent` settings (model, permission mode, allowed tools, turn limit); the runtime adds the workspace, the local database and the strict settings itself. The execution result is output, not a completed run: the coordinator layer that checkpoints and commits it to the service database is a later PR, so this example writes nothing outside the container.

## Runtime transport: exec or an in-container server

The host reaches the runtime two ways. By default `DockerSandbox` starts the container with a sleep entrypoint and every runtime request spawns `python -m agno.sandbox.runtime` through `docker exec`: it works on any image that carries the package and needs no port, but each request is a process through the Docker daemon. With `runtime_port` set, the container's entrypoint is the runtime itself as a small HTTP server, Docker publishes that port on the host's loopback only, and `rpc` becomes a pooled connection: `POST /start`, `POST /poll`, `GET /health`. Same JSON, same journal, same locks; the daemon is used for create, pause, resume, stop and destroy and nothing else. `create` waits for `/health` before handing the sandbox out. The server needs a network, so `runtime_port` is refused with `network="none"`.

```python
sandbox = DockerSandbox("agno-sandbox:local", network="bridge", runtime_port=8765)
# Replicas on other hosts sharing this daemon: advertise the daemon host's address instead.
shared = DockerSandbox("agno-sandbox:local", network="bridge", runtime_port=8765, runtime_host="10.0.0.5")
```

Polls long-poll on both transports: the container holds a `poll` for up to `wait` seconds (default 10, cap 30) and answers as soon as the journal grows or the result lands, so an idle turn costs one request per `wait` and events arrive when they are written. `wait=0` restores the sleep-between-requests loop.

```bash
AGNO_SANDBOX_LOAD_SESSIONS=8 .venv/bin/python cookbook/frameworks/sandbox/runtime_transport_load.py
```

The example runs the same concurrent fixture turns three ways and prints requests per turn, Docker daemon calls per turn and the cost of an idle poll. Requests and daemon calls per turn are what grow with concurrent users; the idle poll is the per-request overhead of the transport. The exec transport with a poll loop is the pre-long-poll behaviour and the reference point.

Every container gets its own bearer token, generated at create, delivered through the private env file and read back onto the handle as `runtime_token`, so any replica holding the handle can talk to the server and nothing else can. The port is published on `runtime_host`, `127.0.0.1` by default, which only this host's replicas reach. With one Docker daemon shared by replicas on several hosts, set `runtime_host` to the daemon host's address those replicas can reach; it is part of the generation's configuration, so every replica must use the same value. The agent inside the container can read its own token, but it can already write the journal directly, so the server gives it no new capability. Hosted providers implement `rpc` against the same server and the same token through whatever port exposure they offer.

## AgentOS as the host: the whole thing working together

```bash
docker run -d -p 6379:6379 redis
./cookbook/scripts/run_pgvector.sh
export ANTHROPIC_API_KEY=...   # or CLAUDE_CODE_OAUTH_TOKEN
.venv/bin/python cookbook/frameworks/sandbox/agentos_sandbox.py

curl -N -X POST http://localhost:7777/agents/coder/runs \
  -F message='Create hello.py that prints hello, run it, reply with only the output' \
  -F session_id=demo -F stream=true
```

`agentos_sandbox.py` is the user-facing shape, reduced to what exists on this branch. On the host there is an AgentOS app with Postgres, Redis and one agent, `SandboxedClaude`, declared like any other agent with a `DockerSandbox` provider, a `runtime_config` for Claude Code and the model credential to forward. The user curls `/agents/coder/runs`, or chats from the AgentOS frontend pointed at this server, and gets the normal SSE stream. The run row lands in Postgres with `metadata.sdk = "sandbox"`. A second turn on the same session resumes the paused container and Claude remembers the first.

Inside the adapter a turn is: find or create the session's container (resume if paused, a new generation if gone), `start` the turn through the runtime client with the run id as the execution id so a retry attaches instead of re-running, deliver the events, take the result, pause the container. The finished `SandboxAgent` adds the lease table, checkpoint restore and the durable queue.

## The relay

The runtime writes a turn's events to its journal and serves them; something outside has to read them. The worker that started the turn can, but a worker can be absent: restarted in a deploy, scaled away, or dead. While nobody reads, the events wait safely in the journal, but nothing reaches Redis, so SSE, `/resume` and dashboards show nothing. `SandboxRelay` is a reader that is always there.

It runs where the service credentials may live, outside every sandbox: inside the AgentOS process, started by the app lifespan, one per replica, as `agentos_sandbox.py` does; or as its own process beside the sandboxes with `python -m agno.sandbox.relay`, which is the shape for production, since an API deploy then never interrupts delivery. It lists the namespace's sandboxes through the provider (`alist`), reads each one's `/health` for running executions (`ahealth`), long-polls every execution from the cursor it last committed, and hands each page to `EventStreamRelaySink`. The sink writes the events into the AgentOS event stream under the run id, the same Redis-backed, indexed stream SSE and `/resume` already read, and commits the journal cursor and the execution result together in `RelayState` (Redis keys under `agno:os:sandbox:`). A relay restart resumes exactly: nothing repeated, nothing skipped. Identity on every page comes from the provider's view of the container, never from the journal. The relay never completes a run; completion is the coordinator's decision after the checkpoint commit.

With a relay, the adapter serves a turn from the event stream instead of polling the container, so the relay is the container's only reader. `SANDBOX_EVENTS_FROM=container` restores direct polling for comparison.

```bash
.venv/bin/python cookbook/frameworks/sandbox/sandbox_takeover.py
```

The takeover example starts AgentOS A, sends a turn whose Claude call runs `sleep 12`, kills A with `SIGKILL` while Claude is inside it, and starts AgentOS B in the same namespace. B's relay resumes from the cursor A committed. The caller reconnects the way a frontend does, `POST /resume` on B with the last index it saw, and receives the events A relayed, the events B relayed, then the result. The run row in Postgres is not completed, because A died before committing and this branch has no coordinator; in the finished stack the queue redelivers the ticket and the next worker reads the result from the event stream and commits.

```bash
.venv/bin/python cookbook/frameworks/sandbox/sandbox_watch.py
```

The watcher prints container state changes and every event the relay writes, live, for a namespace; run it beside the server while chatting from the frontend.

## Process model inside the container, and health

With `runtime_port` set, the container's main process is a supervisor (`python -m agno.sandbox.runtime supervise`) under Docker's init. It runs the HTTP server as a child and restarts it with backoff if it exits. The server is the least important process in the container and the turn's worker the most: workers run detached, so a server crash does not touch them, and the host sees at most a short gap that the cursor-based reconnect absorbs. `SIGTERM`, which Docker sends on `stop`, ends the server and the supervisor; Docker then ends whatever else runs.

`GET /health` reports the server is up and lists the container's executions: id, run id, session id, phase, whether the worker process is alive, whether a result is written, and the journal size. `Sandbox.ahealth(handle)` reads it with the handle's token; `Sandbox.alist()` enumerates a namespace from the daemon's labels.

## Behaviour when a part is missing

What each component does when something it depends on is absent. Items marked *decide* are choices still open.

| Missing or failed | What happens today | Decide |
|---|---|---|
| Runtime server crashes mid-turn | Supervisor restarts it with backoff (0.2 s doubling to 5 s). Worker and journal untouched. Host requests fail until it is back; readers resume from their cursor. Verified live. | Alert after N restarts in a window. |
| Worker (the turn) dies | `poll` and `/health` report it: pid or start time no longer match, `execution_unknown` with no result. | Coordinator fails the turn without re-running the model. |
| Container dies | `inspect` shows exited or gone; `create` on the generation is refused. Turn lost; session recovers into a new generation from the last checkpoint. | None. |
| Host loses the Docker daemon | Every call errors, including `inspect`. Nothing is known about compute. | Coordinator must back off and retry, never treat as a dead container. |
| No AgentOS worker reading | Events wait in the journal; the result waits. With a relay, events and result are already in the event stream; a redelivered ticket finds the result. Without one, the next worker polls from its cursor. | Persist the poll cursor in the lease so a redelivered ticket does not replay from zero. |
| Relay (or its AgentOS process) dies | Nothing lost: journal keeps the bytes, state keeps the last committed cursor. Other replicas' relays continue; a single replica resumes on restart. | Run the relay as its own process so API deploys never pause delivery. |
| Redis down | Relay keeps the cursor where it was and retries; pages are relayed again later, never skipped. Events, cursor and result are written together. | None. |
| Sandbox without a runtime server | `rpc` falls back to exec: works, costs a process per request, stops compute on control failure until #10980's semantics are merged into the fallback. Relay skips it. | Whether exec-only sandboxes are supported in production. |
| No token on the server | Server accepts every reachable caller and warns on stderr. The Docker provider always generates one. | Refuse to start without a token unless bound to loopback. |
| Token refused | 401; `rpc` returns a failed result, `ahealth` raises, relay logs and leaves the sandbox alone. Compute is never touched. | None. |
| Timed-out poll | Raises and leaves compute alone on the HTTP path. | Same on the exec fallback once #10980 lands; pause, if ever, belongs to the coordinator. |
| Two sandboxes on one bridge network | A can reach B's port; the token stops it using it. | ICC-disabled network or one network per session. |

## Boundaries

- The image, Docker daemon and its administrator are trusted. This is not a hostile multitenant isolation service.
- UID/GID 1000, read-only image filesystem, dropped capabilities, no privilege escalation, explicit CPU/memory/process limits, no host filesystem or Docker socket mounts.
- Networking defaults to `none`. Set an operator-managed network or `bridge` explicitly when required. Host and other-container network sharing are rejected. Egress policy and DNS filtering belong to deployment infrastructure.
- Only explicitly configured environment values are added to the image environment. Do not put AgentOS database/Redis credentials in the image or sandbox environment. Image-baked credentials are also visible to repository code.
- `/workspace`, `/runtime` (`HOME`) and `/tmp` are bounded, ephemeral tmpfs. Stopping or removing compute loses these files. A later checkpoint layer must establish durability before completed-turn recovery can be promised.
- Command output is bounded by raw bytes, then decoded with UTF-8 replacement. Timeouts, excessive output, cancellation and uncertain command transport stop the whole container to terminate remote child processes. A stop failure is an infrastructure error requiring reconciliation; do not start a replacement writer until shutdown is confirmed. Completed commands can intentionally leave background applications running.
- Caller cancellation during creation may leave an allocated container. Reconcile by calling `create` again with the same identity/configuration; do not invent another generation until the previous allocation is accounted for.
- `pause` and `resume` are the warm path between turns. A paused container keeps its files, memory and processes under the kernel freezer; `resume` brings the same generation back running with nothing to restore. `create` refuses a paused generation, because only the caller that paused it knows its files are whole; anyone else destroys it and recovers a new generation from the checkpoint. Commands are refused while paused. `stop` and `destroy` remain the cold path and lose the tmpfs files, so a later turn needs a new generation restored from a checkpoint. Pausing does not replace checkpoints: a paused container is still tied to one host.
- No preview, nested Docker, artifact API, shared admission, checkpoint or terminal-success semantics are implied by this sandbox.

## Validation

```bash
.venv/bin/python -m pytest libs/agno/tests/unit/sandbox -q
AGNO_TEST_DOCKER_IMAGE=python:3.12-slim .venv/bin/python -m pytest libs/agno/tests/integration/sandbox -q
```

Integration tests use unique namespaces and remove only their own containers. See [TEST_LOG.md](TEST_LOG.md) for the tested environment and limits.

## Checkpoint archive and storage

```bash
.venv/bin/python cookbook/frameworks/sandbox/checkpoint_files.py
```

This credential-free example captures real filesystem roots, uploads an immutable object, deletes the original files, and restores them through another store instance. `CheckpointArchive` requires `workspace` and `native` roots and a JSON state manifest. `FileCheckpointStore` stores immutable SHA-256-addressed bytes with size/checksum verification and atomic publication. Both classes provide sync and async operations.

Drain native SDK writes and quiesce all applications before capture. The native root must contain only restorable state; keep credentials outside it or explicitly exclude credential paths. Exclusions are exact relative paths (and their descendants), not glob expressions. Ignored and untracked workspace files are included. Safe relative symlinks and file permissions survive; hardlinked source files become separate files. Special files, escaping/cyclic links and malicious archives are rejected. Archive limits bound bytes, entry counts and metadata. Uncompressed tar avoids decompression bombs; restore validates all paths before materializing into a new directory. Restore never updates a running workspace in place.

The object directory and restore parent must be trusted coordinator-owned paths, never mounted into sandbox compute or exposed to agent tools. Production storage must survive the intended failure domain, for example a suitably configured shared filesystem; a service-local directory does not provide host-loss recovery. The demo uses temporary local disk and proves filesystem semantics only. Objects are not deleted when compute is destroyed; retention needs a separate reconciler.

An upload is not a completed run. A following coordinator transaction must publish the checkpoint reference together with authoritative conversation/native metadata and terminal run state, fenced against the current session generation. These archive/store primitives do not implement that transaction, SDK capture, Docker transport or automatic session recovery. Async cancellation waits for in-progress filesystem work to finish, so cleanup does not race a background writer; callers must reconcile whether that operation completed.

## Reconnectable runtime journal

Build the runtime from public package sources only, then run a deterministic fixture:

```bash
.venv/bin/python cookbook/frameworks/sandbox/build_image.py --tag agno-sandbox:local
.venv/bin/python cookbook/frameworks/sandbox/runtime_journal.py
AGNO_TEST_RUNTIME_IMAGE=agno-sandbox:local .venv/bin/python -m pytest libs/agno/tests/integration/sandbox/test_runtime.py -q
```

The build sends a temporary context containing package sources and public packaging files, excluding local environments, credentials and unrelated working-tree files. It pins the Python base digest, Claude SDK, Codex SDK and SQLAlchemy; transitive packages and Debian packages are resolved at build time. Record the resulting image digest and dependency list for deployments. Docker's init process reaps detached runtime children.

`SandboxRuntimeClient` has sync/async start, poll, page iteration, wait and cancel operations. Start identity is `execution_id`, scoped to the session computer; retries with identical configuration/input attach to the existing execution. Different input under the same identity is rejected. The runtime also binds itself to one agent/session and permits one active writer. Its lock is a defensive local check, not a replacement for durable queue admission.

Polling uses byte cursors into the bounded event journal. Reconnecting or replaying does not invoke the SDK again. A completion/poll race cannot hide final events. A dead worker returns `execution_unknown`; callers must reconcile effects before choosing a new execution identity. Poll timeout/cancellation detaches the caller, while explicit runtime cancellation stops the whole computer and loses ephemeral files. Infrastructure transport failure still follows the provider's stop/reconciliation contract.

The deterministic `fixture` SDK requires the explicit test-only environment flag used in the example. It does not call a model. Production runtime requests accept `claude` or `codex` and JSON-compatible adapter configuration. Model/MCP credentials must be explicitly provisioned through the compute environment; broad service credentials must stay outside. SDK retries are disabled here so the coordinator owns retry decisions. Local SQLite is a native-state cache inside the computer; it is not the authoritative AgentOS database. `/runtime/native` contains the local session cache and SDK home directories. Quiesce it before capture, and exclude or separately provision SDK credential files.

Runtime frames deliberately suppress service terminal events. `execution_finished` includes the SDK run and local session metadata; its run may have succeeded, failed or been cancelled. AgentOS must validate the result, capture native/workspace state, fence ownership and atomically commit recovery metadata before publishing a successful terminal event. This PR does not yet register a sandbox agent in AgentOS, import existing Phase 1 sessions, stage remote media, provide historical workspace replay, or implement that durable completion transaction. Live Claude/Codex authentication and native recovery remain separate acceptance work. Do not interpret fixture acceptance as live SDK certification.
