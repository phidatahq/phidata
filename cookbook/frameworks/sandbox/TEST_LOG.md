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

### warm_reuse.py and pause/resume regressions

**Status:** PASS

**Description:** `pause`/`resume` added to the `Sandbox` contract and `DockerSandbox`. `create` refuses a paused generation, because only the caller that paused it knows its files are whole; `resume` is the explicit way back. Unit cases cover pause then create refused and resume returning the same container, resume only from paused, stop and destroy still taking the cold path from paused, and the not-implemented default for providers without a native pause. One real Docker case writes a file, pauses, confirms exec and create are refused, resumes with the file intact, then stops from paused and confirms the generation cannot restart.

**Result:** 36 sandbox unit tests and 7 real Docker cases with `python:3.12-slim` passed. The cookbook passed: the background counter advanced from 7 to 13 across pause and resume, exec and create were refused while paused, create after stop was refused, and generation 2 started empty. `docker_execution.py` passed. `test_command_runner_retains_exit_status_and_bounds_output` failed once with an unrelated intermittent error and passed on five reruns.

---

### checkpoint_files.py and checkpoint regressions

**Status:** PASS

**Description:** Capture conversation metadata, native files and ignored/untracked workspace bytes; upload to an immutable object directory; delete source roots; restore through another store instance. 54 checkpoint tests cover checksums, corruption, missing objects, concurrent upload, partial cleanup, limits, path traversal, hardlink/device rejection, composed symlink escape/cycles, oversized PAX metadata, cancellation draining, credential exclusion through a hardlink and through a root-escaping exclusion, restored timestamps, and cleanup after a failed rename that neither follows a link out of the staged tree nor hides the cause.

**Result:** The cookbook and all 54 checkpoint tests passed on Python 3.9 through 3.14. This layer's files are format- and lint-clean, and type checking reports no new findings. Actual filesystem operations were exercised; no Docker-to-checkpoint transport, live SDK, production shared filesystem or host-loss guarantee was tested by this layer.

---

### checkpoint store protocol, compression and limit symmetry

**Status:** PASS

**Description:** `CheckpointStore` with `FileCheckpointStore` as its first implementation, managed read access through `open_archive`, and gzip-compressed archives by default. 106 checkpoint tests cover the earlier surface and, beyond it: both stored representations round-tripping, and either one read back whatever the reader's own setting is; stored bytes that do not record when a capture ran; two captures of one tree deduplicating to a single object; malformed and hostile compressed archives; expansion stopping at the limit before a whole archive is written; overlapping durable roots refused before anything is written; an absent object raising `CheckpointObjectNotFound` through every sync and async access, while permission, checksum, size and limit failures keep their own types; idempotent deletion; independent lifetimes for repeated and concurrent access, released after a consumer exception and under cancellation; a capture refused when its expanded archive would exceed the limit restore applies to it; an archive whose expanded stream exactly fits still captured and still restored; and an opened object staying readable while retention deletes it.

**Result:** The cookbook and all 106 checkpoint tests passed on Python 3.9, 3.10, 3.11, 3.12, 3.13 and 3.14, with 36 provider tests alongside them. A capture of one unchanged tree produces identical object bytes in both representations on every one of those interpreters, but those bytes differ between 3.9 and 3.12 and later, so objects deduplicate within an interpreter version rather than across a mixed fleet. This layer's files are format- and lint-clean, and type checking reports no new findings. Actual filesystem operations were exercised; no Docker-to-checkpoint transport, live SDK, production shared filesystem or host-loss guarantee was tested by this layer.

---
