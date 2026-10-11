# Sandbox test log

### docker_execution.py

**Status:** PASS

**Description:** Real Docker: create, workspace write/read, reuse, deletion. Credential-free local infrastructure only.

**Result:** Passed on 11 October 2026 with `python:3.12-slim`, resolved digest `python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f`. Used the established `.venvs/claude-dx-validation` environment. No model calls, hosted-provider calls or clean-wheel install performed.

---

### execution provider regression tests

**Status:** PASS

**Description:** `libs/agno/tests/unit/sandbox`: 17 tests covering input validation, explicit environment, deterministic identity, lost creation response, ownership, command limits, failure cleanup and sync wrappers. `libs/agno/tests/integration/sandbox/test_docker.py`: 5 tests using real local containers, including non-root/read-only/no-mount/network configuration, file reuse, exit codes, timeout, output limits, cancellation, concurrent creation/deletion.

**Result:** 17 unit tests and 5 real-container tests passed. Initial real deletion race failed when Docker returned “removal already in progress”; fixed by bounded reconciliation, then the complete suite passed. Required formatting and validation passed. This evidence establishes execution-provider primitives, not durable AgentOS session recovery or live SDK compatibility.

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

### replace_computer.py and checkpoint transfer

**Status:** PASS

**Description:** The cookbook clones a local Git fixture, edits code, runs tests, captures ignored/untracked files and native-state fixtures, destroys compute, restores generation 2, reruns tests, and retrieves an artifact after all compute is gone. 71 sandbox unit tests passed on Python 3.12 and 3.9. The combined 16 real Docker tests cover provider/runtime behavior plus replacement recovery, failure cleanup, stopping a partial restore and a 40 MiB archive beyond the command-output limit.

**Result:** Both required scripts and the cookbook passed. Two real probes established that ordinary container tmpfs produces an empty successful daemon copy, while Docker-managed bounded tmpfs volumes preserve data. The provider now uses the latter and the transport rejects the former. A first restore failed against the read-only container root; restore now targets the writable volumes directly. A synthetic tar fixture initially gave directories non-traversable permissions; corrected the fixture. No live SDK conversation, paid provider, host-loss shared-storage deployment or atomic AgentOS terminal commit was certified.

---

### runtime control transport recovery

**Status:** PASS

**Description:** Runtime start/poll now use a restricted provider RPC operation. A lost control response leaves the session computer available to its current coordinator; arbitrary shell commands retain stop-on-failure behavior. A real-container regression discards a poll response, reconnects through another client and verifies exactly one fixture effect.

**Result:** 74 sandbox unit tests passed on Python 3.12 and 3.9; all 17 real Docker provider/runtime/transfer cases passed. Required scripts passed. This fixes an integration risk where a stale polling request could stop compute during another coordinator's checkpoint. No live model or hosted-provider calls.

---

### durable_completion.py

**Status:** PASS

**Description:** Real local Postgres, unique fixture tables and immutable local archive; staged output remains RUNNING until checkpoint staging and cleanup acknowledgement permit atomic publication. No model calls or real compute in this cookbook.

**Result:** Passed. Companion integration suite: 24 passed across PostgresDb and AsyncPostgresDb, including independent owners, lease expiry, queue attempt fencing, transaction rollback, lost acknowledgement, immutable staged output, deleted/recreated session isolation, external cancellation, and sync entry points. Review found and fixed native metadata overwriting service fields and old-session recovery reuse. Provider shutdown and archive verification remain coordinator responsibilities.

---
