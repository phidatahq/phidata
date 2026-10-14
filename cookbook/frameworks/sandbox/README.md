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
sandbox = DockerSandbox("agno-sandbox:local", network="isolated", runtime_port=8765)
# Replicas on other hosts sharing this daemon: advertise the daemon host's address instead.
shared = DockerSandbox("agno-sandbox:local", network="isolated", runtime_port=8765, runtime_host="10.0.0.5")
```

Polls long-poll on both transports: the container holds a `poll` for up to `wait` seconds (default 10, cap 30) and answers as soon as the journal grows or the result lands, so an idle turn costs one request per `wait` and events arrive when they are written. `wait=0` restores the sleep-between-requests loop.

```bash
AGNO_SANDBOX_LOAD_SESSIONS=8 .venv/bin/python cookbook/frameworks/sandbox/runtime_transport_load.py
```

The example runs the same concurrent fixture turns three ways and prints requests per turn, Docker daemon calls per turn and the cost of an idle poll. Requests and daemon calls per turn are what grow with concurrent users; the idle poll is the per-request overhead of the transport. The exec transport with a poll loop is the pre-long-poll behaviour and the reference point.

Every container gets its own bearer token, generated at create, delivered through the private env file and read back onto the handle as `runtime_token`, so any replica holding the handle can talk to the server and nothing else can. Where the token is inside the container, precisely: the supervisor takes it out of its environment at startup and hands it to the server on stdin, so the serving process holds it only in memory; workers are spawned without it, so the agent's tools do not find it in their environment; every `docker exec` from the host runs with the variable blanked. What remains: the token is delivered through the container's environment so the host can read it back from the daemon, and the exec-time environment of PID 1 and of the supervisor still contains it, readable through `/proc` by anything running as the same UID. A determined agent can therefore still recover it, and it only ever grants what that container's own server does, which the agent can already drive by writing the journal; a sandbox must not be able to reach another sandbox's port (see networking). Running the server under a separate UID is the follow-up that makes the token unreachable. The port is published on `runtime_host`, `127.0.0.1` by default, which only this host's replicas reach and which the container's gateway does not. With one Docker daemon shared by replicas on several hosts, set `runtime_host` to the daemon host's address those replicas can reach; that network must be trusted, since the token travels over plain HTTP, and the value is part of the generation's configuration, so every replica must use the same one. Hosted providers implement `rpc` against the same server and the same token through whatever port exposure they offer.

With `runtime_port` set, the container's main process is a supervisor (`python -m agno.sandbox.runtime supervise`) under Docker's init. It runs the HTTP server as a child and restarts it with backoff if it exits; workers run detached, so a server crash does not touch a turn, and the host sees at most a short gap that the cursor-based reconnect absorbs. `SIGTERM`, which Docker sends on `stop`, ends the server and the supervisor.

```bash
.venv/bin/python cookbook/frameworks/sandbox/runtime_resilience.py
```

The example prints every event as it arrives with its cursor and elapsed time. It runs a fixture turn and shows the variables the turn could see, with the token absent; starts a turn that streams eight events over four seconds, kills the server with `SIGKILL` after the second one, and shows the host's polls failing for a few hundred milliseconds, the supervisor bringing the server back, and the remaining events arriving from the same cursor with nothing missing or repeated; then forces a control request on the exec transport to time out and shows the container still running and the turn still finishing.

Without `runtime_port`, `rpc` falls back to exec with the rule of a control request: a failed or lost reply raises and leaves compute alone, never stopping the container, since start and poll exit on their own and are idempotent. Arbitrary `exec` keeps its stop-on-uncertainty rule. `runtime_port` and `runtime_host` are part of the generation's config digest, so changing them, including flipping a default, makes `create` refuse every live generation; treat such a change as a migration that drains sessions rather than a rolling deploy.

## Boundaries

- The image, Docker daemon and its administrator are trusted. This is not a hostile multitenant isolation service.
- UID/GID 1000, read-only image filesystem, dropped capabilities, no privilege escalation, explicit CPU/memory/process limits, no host filesystem or Docker socket mounts.
- Networking defaults to `none`. A harness that needs the network should use `network="isolated"`: the provider creates one bridge per host, `agno-sandbox`, labelled as Agno-managed, with inter-container traffic off and a pinned subnet (`subnet`, default `172.30.0.0/22`), so sandboxes reach the internet and the host's published ports but not each other. One network serves every namespace on the host: with inter-container traffic off, sharing it adds no reach between sandboxes, and the pinned subnet never draws from Docker's default address pools, which allow only a few dozen networks per host. A `/22` keeps the network under the roughly one thousand interfaces one bridge can carry; a host that needs more sandboxes than that needs a second daemon. Every replica must configure the same subnet; a mismatch, an overlap with another network on the host, or a same-named network the provider did not create each fail with a `SandboxError` that says what to change. `destroy` leaves the network in place and `remove_network` deletes it when nothing is attached. Docker's default `bridge` is accepted but puts every sandbox on `docker0`, where they can reach each other and anything bound on the host; an operator-managed network is accepted as is. Host and other-container network sharing are rejected. The isolated bridge does not block a sandbox from reaching services listening on the host itself; that needs a `DOCKER-USER` firewall rule or binding those services away from the bridge. Egress policy and DNS filtering belong to deployment infrastructure.
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
