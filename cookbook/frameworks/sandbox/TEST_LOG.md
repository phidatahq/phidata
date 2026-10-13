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

**Description:** `pause`/`resume` added to the provider contract and `DockerSandbox`, with `create` on the same identity resuming a paused generation. Four unit cases cover pause then create resuming the same container, resume only from paused, stop and destroy still taking the cold path from paused, and the not-implemented default for providers without a native pause. One real Docker case writes a file, pauses, confirms exec is refused and the state is paused, resumes through `create` with the file intact, then stops from paused and confirms the generation cannot restart. The cookbook adds a background counter to show the frozen process continuing after resume.

**Result:** 100 sandbox unit tests passed on Python 3.12; 7 real Docker provider cases and 7 real runtime cases passed with `python:3.12-slim` and the rebuilt runtime image. The cookbook passed: counter advanced from 6 to 11 across pause and resume, exec while paused refused with the provider's message, create after stop refused, generation 2 started empty. Docker daemon probe confirmed `stop` succeeds on a paused container. No model calls. The coordinator still destroys after every turn; wiring the warm path there is tracked separately.

---

### claude_runtime.py: live two-turn Claude session with a pause

**Status:** PASS

**Description:** Container from `agno-sandbox:local` on `bridge` networking with only `CLAUDE_CODE_OAUTH_TOKEN` forwarded. Turn 1 through `SandboxRuntimeClient` with `sdk="claude"`, `claude-sonnet-4-6`, `bypassPermissions`, tools Read/Write/Bash: Claude wrote `hello.py`, ran it and answered `hello`; Write and Bash tool events and the content arrived through the poll cursor. `/runtime/native` held `.claude`, `.claude.json` and `history.db` after the turn. The container was paused, resumed through `create` with the same identity, and turn 2 asked without tools what the previous turn did.

**Result:** Turn 1 COMPLETED with content `hello`. Turn 2 COMPLETED with "I created `/workspace/hello.py`, which printed `hello`." and the same Claude session id `a4dd9994-...` on the local session row, so the native session resumed rather than restarting. Two live model calls. The container was destroyed at the end; no credential left the host except into that container's environment.

---

