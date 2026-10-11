# Durable sandbox execution

Run coding harnesses in customer-operated Docker computers for trusted teams. Start with `agentos.py` for the integrated durable queue, native/workspace recovery and HTTP API. The smaller examples below exercise each foundation independently. Live model/provider acceptance remains separate from the credential-free fixture tests.

Install the repository development environment and Docker, then run:

```bash
docker pull python:3.12-slim
.venv/bin/python cookbook/frameworks/sandbox/docker_execution.py
```

The example creates a computer, writes and reads a file, reuses that computer and deletes it. No model credentials are needed. Set `AGNO_SANDBOX_IMAGE` to a trusted Linux image containing `python`; pin its digest for repeatable deployments. The Docker context on the service host selects the trusted daemon and its authentication configuration.

`SandboxSpec` identifies the agent, session and generation. The namespace separates deployments on a daemon. Repeating `create` with the same identity and configuration returns the same running computer, including after an uncertain creation response. A stopped generation cannot be restarted through `create`: recovery must allocate a new generation. This prevents accidentally treating lost tmpfs files as retained session state.

The provider offers `create/get/exec/stop/destroy` and their asynchronous `acreate/aget/aexec/astop/adestroy` counterparts. Command arguments are passed as a sequence; explicitly use `sh -c` when shell syntax is intended. Nonzero command exits are returned as `ExecResult`; infrastructure failures raise `SandboxError`. Uncertain commands are never retried automatically.

## Boundaries

- The image, Docker daemon and its administrator are trusted. This is not a hostile multitenant isolation service.
- UID/GID 1000, read-only image filesystem, dropped capabilities, no privilege escalation, explicit CPU/memory/process limits, no host bind mounts or Docker socket mounts.
- Networking defaults to `none`. Set an operator-managed network or `bridge` explicitly when required. Host and other-container network sharing are rejected. Egress policy and DNS filtering belong to deployment infrastructure.
- Only explicitly configured environment values are added to the image environment. Do not put AgentOS database/Redis credentials in the image or sandbox environment. Image-baked credentials are also visible to repository code.
- `/workspace` and `/runtime` (`HOME`) use Docker-managed bounded tmpfs volumes, allowing daemon checkpoint transfer while the computer is paused. `/tmp` is a container tmpfs. Stopping or removing compute loses these files. The integrated coordinator checkpoints these roots before publishing completed-turn success; the provider alone does not provide durability.
- Command output is bounded by raw bytes, then decoded with UTF-8 replacement. Timeouts, excessive output, cancellation and uncertain command transport stop the whole computer to terminate remote child processes. A stop failure is an infrastructure error requiring reconciliation; do not start a replacement writer until shutdown is confirmed. Completed commands can intentionally leave background applications running.
- Caller cancellation during creation may leave an allocated computer. Reconcile by calling `create` again with the same identity/configuration; do not invent another generation until the previous allocation is accounted for.
- No pause/resume, preview, nested Docker, artifact API, shared admission, checkpoint or terminal-success semantics are implied by this provider.

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

Polling uses byte cursors into the bounded event journal. Reconnecting or replaying does not invoke the SDK again. A completion/poll race cannot hide final events. A dead worker returns `execution_unknown`; callers must reconcile effects before choosing a new execution identity. Poll timeout/cancellation detaches the caller, while explicit runtime cancellation stops the whole computer and loses ephemeral files. Runtime control RPC failures leave compute available for reconciliation by its current owner. They never implicitly stop a model turn. Arbitrary command execution retains its stop-on-failure behavior. Providers implementing runtime support must supply `rpc/arpc`; unsupported providers fail explicitly rather than fall back to a shell command.

The deterministic `fixture` SDK requires the explicit test-only environment flag used in the example. It does not call a model. Production runtime requests accept `claude` or `codex` and JSON-compatible adapter configuration. Model/MCP credentials must be explicitly provisioned through the compute environment; broad service credentials must stay outside. SDK retries are disabled here so the coordinator owns retry decisions. Local SQLite is a native-state cache inside the computer; it is not the authoritative AgentOS database. `/runtime/native` contains the local session cache and SDK home directories. Quiesce it before capture, and exclude or separately provision SDK credential files.

Runtime frames deliberately suppress service terminal events. `execution_finished` includes the SDK run and local session metadata; its run may have succeeded, failed or been cancelled. AgentOS must validate the result, capture native/workspace state, fence ownership and atomically commit recovery metadata before publishing a successful terminal event. This PR does not yet register a sandbox agent in AgentOS, import existing Phase 1 sessions, stage remote media, provide historical workspace replay, or implement that durable completion transaction. Live Claude/Codex authentication and native recovery remain separate acceptance work. Do not interpret fixture acceptance as live SDK certification.


## Destroy and replace a session computer

```bash
AGNO_SANDBOX_IMAGE=agno-sandbox:local .venv/bin/python cookbook/frameworks/sandbox/replace_computer.py
```

The example clones a deterministic local Git fixture, edits tracked code, runs its tests, and creates ignored/untracked files and a native-state fixture. It captures one immutable checkpoint, destroys compute and its volumes, restores into generation 2, reruns the application tests, then retrieves an artifact after all compute is gone. No network or model credentials are required.

`DockerCheckpointTransfer` provides sync/async capture and restore. Capture pauses compute for two bounded raw archive exports, resumes it, then validates and uploads the combined archive. Docker never extracts an untrusted archive on the service host. Restore verifies the immutable checkpoint, requires an empty computer, and writes directly into the writable managed volumes while preserving UID 1000 access. Failure after partial restoration stops that generation. The managed roots retain their configured ownership/permissions; permissions beneath the roots are restored.

Plain container tmpfs is rejected by the transport: Docker can return a successful but empty copy for it. The provider now creates labeled, bounded, daemon-visible tmpfs volumes and verifies their configuration on reuse. Destruction removes only matching owned volumes, including recovery after a lost container-removal response. A failed create before a container exists may leave labeled empty volumes; reconcile the same creation identity before deciding to clean up an orphan. These volumes still provide no host-loss durability; the external checkpoint store does.

The caller must hold exclusive generation ownership and finish/drain the SDK before capture. Applications requiring logical database backups need an explicit quiesce/backup procedure; pausing processes only establishes a filesystem capture boundary. No nested-container or anonymous-volume data is included. Current capture uses local staging space for raw and combined archives in the coordinator's object directory; provision several times the checkpoint byte limit per concurrent capture. A transfer is bounded to 120 seconds per root. These limits intentionally fail finalization rather than publish an incomplete recovery point.

The known Codex `auth.json` and Claude `.credentials.json` paths are excluded by default. These defaults are not a secret scanner: use explicit exclusions or keep other credentials outside durable roots. Passing `exclude` replaces the default list. Keep native credentials provisioned separately for restored compute. Atomic run/conversation/checkpoint publication still belongs to the following AgentOS coordinator layer.

### Atomic completion store

`durable_completion.py` exercises the Postgres ownership/finalization contract using fixture output and an actual archive. Set `AGNO_TEST_SANDBOX_DB_URL` to a dedicated local test database. It creates unique tables and removes them afterwards. The store supports both Postgres adapters asynchronously; synchronous entry points require `PostgresDb`.

A runtime result is staged first. A verified checkpoint reference and provider-confirmed compute cleanup are required before one transaction publishes the run and session recovery reference. Lease epochs and queue attempts fence previous coordinators. Native metadata is nested under `session_data.sandbox.native`; runtime data cannot replace control-plane session fields. Recreating a deleted session requires explicit reconciliation of its old registry/compute; it cannot silently inherit that state.

This PR supplies the storage contract, not the AgentOS coordinator. The caller still verifies checkpoint bytes, binds the correct manifest, renews leases, and confirms provider cleanup. Local checkpoint directories need deployment-specific durable storage before claiming host-loss recovery.

The runtime forces `require_native_resume=True` and `strict_persistence=True` on Claude/Codex adapters. Missing native state is an error; successful-turn history must not silently seed a new native conversation. Codex ephemeral threads are incompatible with this contract. The runtime reads back its local SQLite result before returning execution output. Ordinary SDK users keep the existing fallback defaults unless they explicitly enable these options.

### Session computer coordinator

`session_computer.py` runs two fixture turns through the complete Docker/Postgres path. Build the runtime, then set `AGNO_TEST_RUNTIME_IMAGE` and `AGNO_TEST_SANDBOX_DB_URL` before running it. No model credentials are used. The second turn restores the first turn's workspace onto a replacement computer.

`SandboxCoordinator` stages the execution result before capturing an archive, persists that reference before removing compute, and atomically publishes conversation plus recovery metadata afterwards. A reconnect uses the same execution identity; a finalization retry never starts another model turn. Missing compute before capture fails visibly and preserves the previous checkpoint. A missing cleanup or commit acknowledgement can be reconciled with the same run ID and input. `run()` requires PostgresDb; `arun()` supports both Postgres adapters.

Provider mutation operations hold the session ownership rows until their bounded transport calls drain. Takeover waits for an in-flight restore/capture instead of racing it. This costs a database connection and can delay cancellation until a transfer finishes. The initial implementation uses cold replacement after every completed turn; no warm-computer reuse is claimed.

Use deployment storage accessible to every coordinator replica for checkpoint bytes. The local directory store in these examples is temporary and does not certify host-loss recovery. Workspace and native files restore; live processes restart, and remote MCP/tool effects are not rolled back. Direct stream reconnection may repeat provisional events; durable event transport remains an AgentOS integration responsibility.

## AgentOS API execution

`agentos.py` registers `SandboxAgent` with a durable Postgres queue and shared Redis cancellation/event transport. Foreground, streaming and background API requests all submit to the queue; losing the HTTP connection does not cancel the worker. Independent sessions run concurrently; overlapping turns in one session wait without consuming attempts. Direct Python `run`/`arun` use the coordinator's Postgres fence. Python background submission requires the active AgentOS queue.

Build the runtime image with `build_image.py`, install `psycopg[binary]`, `redis`, `docker` CLI, `fastapi` and `uvicorn` in the service environment, and configure:

```bash
export SANDBOX_DATABASE_URL=postgresql+psycopg://ai:ai@localhost:5573/ai
export SANDBOX_REDIS_URL=redis://localhost:6407/0
export SANDBOX_CHECKPOINT_DIRECTORY=/absolute/path/to/durable/shared/checkpoints
export SANDBOX_RUNTIME_IMAGE=agno-sandbox:local
export SANDBOX_HARNESS=fixture
.venv/bin/python cookbook/frameworks/sandbox/agentos.py
```

The fixture harness makes no model calls. For a real harness select `claude` or `codex` and configure its model API key. The example enables Docker bridge networking for those harnesses; customer network policy must control its egress. Every replica must reach the same Docker daemon, checkpoint storage, Postgres and Redis and use identical runtime configuration. Multiple independent Docker daemons are not interchangeable for an active computer. Local checkpoint directories do not provide host-loss durability unless backed by shared durable storage.

```bash
curl -X POST http://localhost:7777/agents/coder/runs \
  -H 'Idempotency-Key: first-turn' \
  -F session_id=example -F message='Create a small application and test it' \
  -F stream=false -F background=true
```

Keep the returned run ID. Reconnect with `POST /agents/coder/runs/{run_id}/resume` using form fields `session_id` and optionally `last_event_index`; cancel with `POST /agents/coder/runs/{run_id}/cancel?session_id=example`. Reusing an idempotency key requires the same session ID, input and options. Conflicting submissions return 409. Streaming terminal success follows the durable checkpoint commit. Retained indexed events support replay after the live Redis view expires; content deltas follow the agent's `events_to_skip` policy.

This slice accepts text and JSON runtime configuration, including structured-output schemas. File/image inputs, step replay/fork, version-pinned instances and arbitrary per-turn SDK options are explicitly rejected pending checkpoint-aware integrations. The ordinary session deletion API refuses sessions with retained sandbox recovery; purge their recovery data first using the lifecycle API below. A failed checkpoint upload retries finalization without repeating the model. If the configured queue attempts are exhausted, compute is removed and the turn fails visibly while retaining the previous checkpoint. External effects can still repeat after execution crashes and need application idempotency.


## Status and artifacts after compute removal

`GET /agents/{agent_id}/sessions/{session_id}/sandbox` reports the persisted phase, generation, active run, last completed run and whether compute/checkpoint references exist. It is a database view, not a provider health probe. `GET .../sandbox/artifacts?offset=0&limit=100` lists regular workspace files. `GET .../sandbox/artifact?path=relative/path` downloads a file from the last completed checkpoint, including while a newer turn runs. Responses identify the checkpoint and run; no compute is provisioned.

```bash
.venv/bin/python cookbook/frameworks/sandbox/download_artifact.py \
  --session example --path fixture-effects.txt --output /tmp/completed-effects.txt
```

Run a fixture turn in `agentos.py` first. `SANDBOX_API_URL` overrides the server URL and `SANDBOX_BEARER_TOKEN` supplies authentication when configured. Existing output files are never overwritten. HTTP routes use AgentOS agent-run permission and configured user isolation; service code can use the exact-owner `SandboxArtifacts.status/list/read` and async variants. Downloads are bounded to 8 MiB by default, served as attachments, and reject symlinks, traversal and native runtime state. Archive checksum and session-incarnation identity are verified before reading. Missing storage fails visibly. Listing pagination bounds the response; archive validation still scans the bounded checkpoint.

These are read operations. Compute retirement and recovery deletion are explicit operations below; downloading an artifact never deletes data.


## Retire compute and delete recovery data

`POST .../sandbox/retire` cancels the active run and reconciles compute removal, retaining the last completed checkpoint. It is idempotent for idle sessions. A later turn can allocate replacement compute from that checkpoint. The response describes the retired run; it does not pause admission of future turns.

`DELETE .../sandbox/recovery` permanently retires the session identity and deletes its published workspace/native checkpoint objects. It requires an idle session; retire an active run first. A database tombstone blocks new execution before storage deletion starts. If storage cleanup fails, retry the same operation; the session stays retired and ordinary conversation deletion stays blocked until cleanup completes. Each object is checked against the exact session incarnation before removal. A new session needs a new ID.

Recovery deletion retains conversation/tool audit history. After it succeeds, the ordinary `DELETE /sessions/{session_id}` endpoint can delete that history. Both Postgres adapters protect this ordering inside their deletion transactions, including bulk deletion. Unreferenced uploads, provider logs, storage backups and external tool effects are outside this published-checkpoint deletion operation; their retention is a separate operator policy. Automatic idle/retention scheduling, fleet quotas and warm reuse are not enabled by these APIs.

With the `agentos.py` fixture server running, this example creates and deletes only its own fresh session:

```bash
.venv/bin/python cookbook/frameworks/sandbox/retire_recovery.py
```

Library code can use `SandboxLifecycle.retire/delete_recovery` or `aretire/adelete_recovery`. Ownership is exact, including `user_id=None`; synchronous entry points require `PostgresDb`.
