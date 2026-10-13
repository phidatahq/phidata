# Sandbox test log

### docker_execution.py

**Status:** PASS

**Description:** Real Docker: create, workspace write/read, reuse, deletion. Credential-free local infrastructure only.

**Result:** Passed on 11 October 2026 with `python:3.12-slim`, resolved digest `python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f`. Used the established `.venvs/claude-dx-validation` environment. No model calls, hosted-provider calls or clean-wheel install performed.

---

### sandbox regression tests

**Status:** PASS

**Description:** `libs/agno/tests/unit/sandbox`: 17 tests covering input validation, explicit environment, deterministic identity, lost creation response, ownership, command limits, failure cleanup and sync wrappers. `libs/agno/tests/integration/sandbox/test_docker.py`: 5 tests using real local containers, including non-root/read-only/no-mount/network configuration, file reuse, exit codes, timeout, output limits, cancellation, concurrent creation/deletion.

**Result:** 17 unit tests and 5 real-container tests passed. Initial real deletion race failed when Docker returned “removal already in progress”; fixed by bounded reconciliation, then the complete suite passed. Required formatting and validation passed. This evidence establishes sandbox primitives, not durable AgentOS session recovery or live SDK compatibility.

---

### checkpoint_files.py and checkpoint regressions

**Status:** PASS

**Description:** Capture conversation metadata, native files and ignored/untracked workspace bytes; upload to an immutable object directory; delete source roots; restore through another store instance. 28 checkpoint tests cover checksums, corruption, missing objects, concurrent upload, partial cleanup, limits, path traversal, hardlink/device rejection, composed symlink escape/cycles, oversized PAX metadata and cancellation draining.

**Result:** The cookbook and all 45 sandbox unit tests (28 checkpoint + 17 Docker) passed in `.venvs/claude-dx-validation`. Both required scripts passed. Actual filesystem operations were exercised; no Docker-to-checkpoint transport, live SDK, production shared filesystem or host-loss guarantee was tested by this layer.

---

### runtime_journal.py and runtime protocol acceptance

**Status:** PASS

**Description:** 19 new runtime/client tests cover duplicate dispatch, one-writer locking, event replay, dead-worker uncertainty, incomplete frames, execution timeout, protocol/identity validation, sync/async clients, poll cancellation and a final-event/completion race. All 64 sandbox unit tests passed on Python 3.12 and Python 3.9. Real Docker: 11 combined provider/runtime cases plus one SDK-construction case passed; the reconnect cookbook passed. The construction check instantiates both adapters without authenticating or calling models.

**Result:** Runtime image `sha256:616c3e78f2e95c6e81eda400222ec142ebfffa2383412fcede3a97f966b42317`, Claude SDK 0.2.165, Codex SDK 0.162.1, SQLAlchemy 2.0.52. Required scripts passed in the established validation environment. The initial image build hit an HTTP Debian mirror checksum mismatch; switching the official mirror to HTTPS resolved it with verification retained. The initial SDK-construction assertion inspected a nullable configuration field instead of the engine; corrected the assertion and reran successfully. No live model calls, hosted provider calls or full AgentOS sandbox durability acceptance.

---

### warm_reuse.py and pause/resume regressions

**Status:** PASS

**Description:** `pause`/`resume` added to the provider contract and `DockerSandbox`; `create` refuses a paused generation so only its owner resumes it. Four unit cases cover pause then create refused and resume returning the same container, resume only from paused, stop and destroy still taking the cold path from paused, and the not-implemented default for providers without a native pause. One real Docker case writes a file, pauses, confirms exec and create are refused while paused, resumes with the file intact, then stops from paused and confirms the generation cannot restart. The cookbook adds a background counter to show the frozen process continuing after resume.

**Result:** 100 sandbox unit tests passed on Python 3.12; 7 real Docker provider cases and 7 real runtime cases passed with `python:3.12-slim` and the rebuilt runtime image. The cookbook passed: counter advanced from 6 to 11 across pause and resume, exec while paused refused with the provider's message, create after stop refused, generation 2 started empty. Docker daemon probe confirmed `stop` succeeds on a paused container. No model calls. The coordinator still destroys after every turn; wiring the warm path there is tracked separately.

---

### claude_runtime.py: live two-turn Claude session with a pause

**Status:** PASS

**Description:** Container from `agno-sandbox:local` on `bridge` networking with only `CLAUDE_CODE_OAUTH_TOKEN` forwarded. Turn 1 through `SandboxRuntimeClient` with `sdk="claude"`, `claude-sonnet-4-6`, `bypassPermissions`, tools Read/Write/Bash: Claude wrote `hello.py`, ran it and answered `hello`; Write and Bash tool events and the content arrived through the poll cursor. `/runtime/native` held `.claude`, `.claude.json` and `history.db` after the turn. The container was paused, resumed explicitly, and turn 2 asked without tools what the previous turn did.

**Result:** Turn 1 COMPLETED with content `hello`. Turn 2 COMPLETED with "I created `/workspace/hello.py`, which printed `hello`." and the same Claude session id `a4dd9994-...` on the local session row, so the native session resumed rather than restarting. Two live model calls. The container was destroyed at the end; no credential left the host except into that container's environment.

---

### create no longer resumes a paused generation

**Status:** PASS

**Description:** Reviewed the restore sequence in the checkpoint transfer and the coordinator's provisioning order: a container is bound to the session lease only after restore completes, so a restore that died halfway leaves an unbound paused container. A `create` that revived any paused container would hand such a container back as healthy. `create` now raises "paused; resume it or destroy it" and `resume` is the only way back to running. Reproduced the hazard on a real container before the change: paused, half-copied, then `create` returned it running with incomplete roots.

**Result:** Unit and real Docker cases updated for the explicit resume; both Claude cookbooks and the warm-reuse cookbook call `resume`. 100 sandbox unit tests and 7 real Docker provider cases passed after the change; the warm-reuse cookbook passed with the refused `create` printed. The warm Claude cookbook was re-run live and passed with the explicit resume (same native session id across turns); the cold Claude cookbook does not pause and was re-linted only.

---

### Runtime served over HTTP, long-poll, and the transport load comparison

**Status:** PASS

**Description:** The runtime gains a `serve` operation, a stdlib threaded HTTP server run as the container entrypoint with `POST /start`, `POST /poll` and `GET /health` over the same JSON and journal, plus a `wait` long-poll on both transports. `DockerSandbox(runtime_port=...)` publishes the port on the host loopback, waits for `/health` on create, and routes `rpc` over a pooled `httpx` client with no daemon call per request; without a port, `rpc` falls back to spawning the runtime over exec. `SandboxHandle` carries `runtime_url`. The client goes through `rpc` and long-polls by default (10 s, cap 30 s). Two fixes found while measuring: the stdlib server's reverse DNS lookup on bind stalled five seconds per server (skipped), and headers and body written as two segments hit the delayed-ACK stall (TCP_NODELAY set).

**Result:** 110 sandbox unit tests passed in 3 s, including an in-process runtime server (health, idempotent start, conflict, long-poll returning on journal growth, malformed and oversized requests), stdin long-poll, the Docker HTTP path over a mock transport (publish args, serve entrypoint, label, readiness, failures leaving compute alone, zero daemon calls per request, exec fallback) and configuration validation. Runtime integration cases run over both transports: 15 passed, 1 skipped (exec-only skip of the long-poll case). Docker provider cases: 7 passed. `runtime_journal.py`, `warm_reuse.py` and the live `claude_runtime.py` over HTTP passed. `runtime_transport_load.py` with 8 concurrent 3 s fixture turns on Docker Desktop for Mac:

| transport | requests/turn | daemon calls/turn | idle poll p50 |
|---|---|---|---|
| exec, poll loop (previous behaviour) | 9.0 | 18.0 | 151 ms |
| exec, long-poll | 2.0 | 4.0 | 138 ms |
| http, long-poll | 2.0 | 0.0 | 1.7 ms |

No model calls in the load run. Requests and daemon calls per turn are what scale with concurrent users; at 1,000 concurrent turns the poll loop would put thousands of exec spawns per second through one dockerd, while HTTP keeps the daemon off the hot path entirely.

---

### Runtime server token and advertised host

**Status:** PASS

**Description:** The HTTP transport assumed the daemon and the replica share a machine: the port was published and advertised on `127.0.0.1`, so a replica on another host sharing a remote daemon would never reach it and `create` would fail waiting for health. `DockerSandbox` gains `runtime_host` (published on and advertised as that address, part of the config digest) and every container a per-container bearer token: generated at create, passed through the private env file, read back from the container environment onto `SandboxHandle.runtime_token` (kept out of repr), sent on every request including the readiness check, and required by the server for every path. A user env entry with the token name is refused.

**Result:** Unit cases cover token generation and read-back, requests carrying the header and a stale token refused, the server returning 401 without or with a wrong token and 200 with the right one, `runtime_host` publishing and advertising the daemon host's address, validation of bad hosts, and the three configurations yielding distinct digests. Integration: an anonymous request to a live container's server is refused with 401 and the owner's request answers 200; all runtime cases pass over both transports. No change to the load numbers.

---

### Relay, supervisor, health listing, AgentOS host and takeover

**Status:** PASS

**Description:** `SandboxRelay` follows every execution of a namespace (provider `alist` and `ahealth`, long-poll per execution) and writes pages through `EventStreamRelaySink` into the AgentOS event stream, committing the journal cursor and the result in `RelayState` (memory or Redis). The runtime's `/health` lists executions with worker liveness; the container's main process is a supervisor that restarts the server and ends on SIGTERM. `agentos_sandbox.py` registers a `SandboxedClaude` external agent on a real AgentOS with Postgres and Redis, runs the relay in the app lifespan, and serves turns from the event stream. `sandbox_takeover.py` kills AgentOS mid-turn and reads the turn back through a second AgentOS's `/resume`.

**Result:** 121 sandbox unit tests passed: relay discovery into the event stream with indices and the run registered but never completed, resume from the committed cursor after a failed poll, skipping sandboxes without a server or paused, tolerating a refused token, stopping on signal, unknown event types skipped; health listing with worker liveness; supervisor restart with backoff and SIGTERM. Runtime integration over both transports: 18 passed, 4 exec-only skips, including the server killed mid-turn with the worker surviving and the turn finishing once, and a fixture turn relayed into an in-memory event stream with nobody polling. Takeover live: A relayed indices 0 and 1 (cursor 990) and was killed at 6.3 s; B up at 9.9 s; `/resume` on B replayed 0 and 1 and delivered 2 (ToolCallCompleted, 18.3 s) and 3 (RunContent "done", 19.8 s) live; relay state cursor 2007, result `execution_finished`. One model call. Earlier hangs were a stale AgentOS holding port 7802 from a previous run; the driver now reconnects to `/resume` in short rounds with the last index seen, as a frontend does.

---

