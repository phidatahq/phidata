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

This credential-free example captures real filesystem roots, uploads an immutable object, deletes the original files, and restores them through another store instance. `CheckpointArchive` requires `workspace` and `native` roots and a JSON state manifest. `FileCheckpointStore` stores immutable SHA-256-addressed bytes with size/checksum verification and atomic publication, and is the first implementation of the `CheckpointStore` protocol. Reading an object that storage no longer holds raises `CheckpointObjectNotFound`, so a service can tell storage loss apart from a checkpoint it merely cannot serve. Read an object back through `open_archive`, which verifies it and then yields a path valid for the duration of the context, which retention removing the object meanwhile does not invalidate; a store whose objects are remote materializes a temporary copy there and removes it on exit, while a local object is never removed by reading it. Both classes provide sync and async operations.

Drain native SDK writes and quiesce all applications before capture. The native root must contain only restorable state; keep credentials outside it or explicitly exclude credential paths. Exclusions are exact relative paths (and their descendants), not glob expressions. The two roots must be disjoint, and capture refuses them otherwise: an exclusion names one archive prefix, so a root containing the other would carry an excluded file in under that other prefix. Capture also refuses a hardlink that would carry an excluded file's contents out under another name, for as long as the excluded path itself exists; once the original is deleted a surviving link cannot be told from an ordinary file, so break such links rather than relying on the exclusion. Ignored and untracked workspace files are included. Safe relative symlinks, file permissions and modification times survive; hardlinked source files become separate files. Special files, escaping/cyclic links and malicious archives are rejected. Archives are gzip-compressed by default; `CheckpointArchive(compress=False)` writes plain tar, and either stored representation is read back whatever the reader's own setting is. Archive limits bound bytes, entry counts and metadata. The byte limit measures the expanded archive, entry framing included, on write as much as on read: a capture that succeeds is one restore accepts, and a decompression bomb is rejected before it is written. The digest and size in a reference always describe the stored bytes. Restore validates all paths before materializing into a new directory. Restore never updates a running workspace in place.

The object directory and restore parent must be trusted coordinator-owned paths, never mounted into sandbox compute or exposed to agent tools. Production storage must survive the intended failure domain, for example a suitably configured shared filesystem; a service-local directory does not provide host-loss recovery. The demo uses temporary local disk and proves filesystem semantics only. Objects are not deleted when compute is destroyed; `delete` exists for a retention reconciler, which is separate and does not ship here.

### Required filesystem capabilities

Checkpoint file reads require `os.O_NOFOLLOW`; the implementation refuses to read without it instead of following a symlink. `FileCheckpointStore` also requires hard links for immutable publication and reader leases, file and directory `fsync` for durability, and atomic rename for archive restore. Restoring symlinks requires symlink creation and timestamp updates with `follow_symlinks=False`. These requirements apply to the host running the checkpoint code and its filesystem, regardless of the Docker container image.

A missing `O_NOFOLLOW`, or an explicitly unsupported hard-link or directory-sync operation, raises an actionable `SandboxError`. The underlying operation error is retained as its cause. Permission, disk-full and other I/O errors propagate unchanged; no protection or durability step is silently skipped. Capabilities are checked when used, not certified at construction: a failed directory sync can occur after an object has been linked or deleted, so an error does not mean nothing changed. Do not publish a checkpoint reference from a failed upload.

Windows support has not been established or tested for this checkpoint implementation. These checks report unavailable primitives; they do not add a Windows fallback. Use a host and filesystem that provide the required capabilities.

An upload is not a completed run. A following coordinator transaction must publish the checkpoint reference together with authoritative conversation/native metadata and terminal run state, fenced against the current session generation. These archive/store primitives do not implement that transaction, SDK capture, Docker transport or automatic session recovery. Async cancellation waits for in-progress filesystem work to finish, so cleanup does not race a background writer; callers must reconcile whether that operation completed.
