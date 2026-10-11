"""Linux runtime protocol. Execute in the sandbox image, never on an AgentOS API host.

The compute provider authenticates transport. This process has no control-plane
credentials. Its journal reports execution finished, not durable run completion.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator

from agno.sandbox.base import SandboxError
from agno.sandbox.protocol import validate_request as _validate

_VERSION = 1
_MAX_REQUEST = 1024 * 1024
_MAX_FRAME = 256 * 1024
_MAX_RESULT = 1024 * 1024
_MAX_JOURNAL = 16 * 1024 * 1024
_TERMINAL_EVENTS = {"RunCompleted", "RunError", "RunCancelled"}


def _encode(value: Any) -> bytes:
    return json.dumps(value, allow_nan=False, separators=(",", ":")).encode()


def _atomic(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _job(root: Path, execution_id: str) -> Path:
    if not isinstance(execution_id, str) or not execution_id or len(execution_id) > 256:
        raise ValueError("Invalid runtime execution identity")
    return root / "jobs" / hashlib.sha256(execution_id.encode()).hexdigest()


@contextmanager
def _lock(path: Path) -> Iterator[None]:
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SandboxError("Runtime session already has a writer") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _process_start(pid: int) -> str | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (FileNotFoundError, IndexError):
        return None


def _start(root: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    _validate(request)
    if _process_start(os.getpid()) is None:
        raise SandboxError("Sandbox runtime requires Linux process identity tracking")
    (root / "jobs").mkdir(parents=True, exist_ok=True)
    directory = _job(root, request["execution_id"])
    payload = _encode(request)
    with _lock(root / "dispatch.lock"):
        identity_path = root / "identity.json"
        identity = _encode({key: request[key] for key in ("agent_id", "session_id")})
        if identity_path.exists() and identity_path.read_bytes() != identity:
            raise SandboxError("A runtime computer belongs to exactly one agent/session")
        if not identity_path.exists():
            _atomic(identity_path, identity)
        if directory.exists():
            if (directory / "request.json").read_bytes() != payload:
                raise SandboxError("Execution identity already exists with different input")
            return {"version": _VERSION, "execution_id": request["execution_id"], "accepted": True}
        directory.mkdir(mode=0o700)
        _atomic(directory / "request.json", payload)
        _atomic(directory / "status.json", _encode({"phase": "starting", "created_at": time.time()}))
        try:
            subprocess.Popen(
                [sys.executable, "-I", "-m", "agno.sandbox.runtime", "worker", str(directory)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        except Exception as error:
            _atomic(directory / "result.json", _encode({"type": "execution_error", "error": str(error)}))
            raise
    return {"version": _VERSION, "execution_id": request["execution_id"], "accepted": True}


def _append(directory: Path, event: Dict[str, Any]) -> None:
    payload = _encode({"type": "event", "event": event}) + b"\n"
    if len(payload) > _MAX_FRAME:
        raise SandboxError("Runtime event exceeds its frame limit")
    path = directory / "events.jsonl"
    with path.open("ab") as stream:
        if stream.tell() + len(payload) > _MAX_JOURNAL:
            raise SandboxError("Runtime event journal exceeds its limit")
        stream.write(payload)
        stream.flush()


async def _fixture(directory: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    workspace = Path(os.environ.get("AGNO_SANDBOX_WORKSPACE", "/workspace"))
    workspace.mkdir(exist_ok=True)
    from agno.agents._media import stage_media
    from agno.sandbox.media import decode_media

    stage_media(workspace, request["run_id"], decode_media(request.get("media", [])))
    with (workspace / "fixture-effects.txt").open("a") as stream:
        stream.write(request["run_id"] + "\n")
    await asyncio.sleep(float(request.get("config", {}).get("delay", 0)))
    event = {
        "event": "RunContent",
        "content": request["input"],
        "run_id": request["run_id"],
        "session_id": request["session_id"],
        "agent_id": request["agent_id"],
    }
    _append(directory, event)
    return {
        "type": "execution_finished",
        "run": {
            "run_id": request["run_id"],
            "session_id": request["session_id"],
            "agent_id": request["agent_id"],
            "user_id": request.get("user_id"),
            "status": "COMPLETED",
            "content": request["input"],
        },
        "session": {
            "session_id": request["session_id"],
            "user_id": request.get("user_id"),
            "session_data": {"fixture": True},
        },
    }


def _agent(request: Dict[str, Any], native: Path) -> Any:
    from agno.db.sqlite import SqliteDb

    # This local database is native runtime state, not the authoritative service
    # database. It has no network credentials and is checkpointed after SDK drain.
    db = SqliteDb(db_file=str(native / "history.db"))
    config = dict(request.get("config", {}))
    config.update(
        id=request["agent_id"],
        cwd="/workspace",
        db=db,
        retries=0,
        keep_uploads=True,
        require_native_resume=True,
        strict_persistence=True,
        store_events=True,
    )
    if request["sdk"] == "claude":
        from agno.agents.claude import ClaudeAgent

        return ClaudeAgent(**config)
    from agno.agents.codex import CodexAgent

    return CodexAgent(**config)


async def _execute(directory: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    if request["sdk"] == "fixture":
        return await _fixture(directory, request)
    from agno.run.agent import RunOutput

    native = directory.parent.parent / "native"
    native.mkdir(exist_ok=True)
    os.environ["HOME"] = str(native)
    codex_home = native / "codex"
    if request["sdk"] == "codex":
        codex_home.mkdir(mode=0o700, exist_ok=True)
    os.environ["CODEX_HOME"] = str(codex_home)
    from agno.sandbox.media import decode_media

    agent = _agent(request, native)
    run = None
    try:
        if request["sdk"] == "codex" and os.environ.get("OPENAI_API_KEY"):
            # Fresh computers have no native auth file; reauthenticate after every restore.
            await agent.alogin_api_key(os.environ["OPENAI_API_KEY"])
        async for event in agent.arun(
            request["input"],
            run_id=request["run_id"],
            session_id=request["session_id"],
            user_id=request.get("user_id"),
            stream=True,
            stream_events=True,
            yield_run_output=True,
            **decode_media(request.get("media", [])),
        ):
            if isinstance(event, RunOutput):
                run = event
            elif event.event not in _TERMINAL_EVENTS:
                _append(directory, event.to_dict())
        if run is None:
            raise SandboxError("SDK runtime did not produce an execution result")
        session = agent.get_session(request["session_id"], user_id=request.get("user_id"))
        if session is None:
            raise SandboxError("SDK runtime did not retain native session metadata")
        persisted = agent.db.get_run(request["run_id"])
        if (
            persisted is None
            or RunOutput.from_dict(persisted.to_dict()).to_dict() != RunOutput.from_dict(run.to_dict()).to_dict()
        ):
            raise SandboxError("SDK runtime did not durably retain its exact execution result")
        return {"type": "execution_finished", "run": run.to_dict(), "session": session.to_dict(include_runs=False)}
    finally:
        agent.db.db_engine.dispose()


def _worker(directory: Path) -> None:
    request = json.loads((directory / "request.json").read_bytes())
    root = directory.parent.parent
    try:
        _validate(request)
        with _lock(root / "execution.lock"):
            _atomic(
                directory / "status.json",
                _encode({"phase": "running", "pid": os.getpid(), "start": _process_start(os.getpid())}),
            )

            async def bounded_execute() -> Dict[str, Any]:
                return await asyncio.wait_for(_execute(directory, request), request.get("execution_timeout", 900))

            result = asyncio.run(bounded_execute())
            payload = _encode(result)
            if len(payload) > _MAX_RESULT:
                raise SandboxError("Runtime execution result exceeds its limit")
            _atomic(directory / "result.json", payload)
    except Exception as error:
        _atomic(
            directory / "result.json",
            _encode({"type": "execution_error", "error": (str(error) or type(error).__name__)[:2000]}),
        )


def _poll(root: Path, execution_id: str, cursor: int) -> Dict[str, Any]:
    if type(cursor) is not int or cursor < 0:
        raise ValueError("Runtime cursor must be a nonnegative integer")
    directory = _job(root, execution_id)
    request = json.loads((directory / "request.json").read_bytes())
    if request["execution_id"] != execution_id:
        raise SandboxError("Runtime execution identity mismatch")
    # Snapshot the immutable finish marker before reading events. If completion
    # races this poll, the next poll drains its final events before exposing it.
    result_path = directory / "result.json"
    result_ready = result_path.exists()
    frames = []
    path = directory / "events.jsonl"
    if path.exists():
        with path.open("rb") as stream:
            if cursor > os.fstat(stream.fileno()).st_size:
                raise ValueError("Runtime cursor exceeds journal length")
            stream.seek(cursor)
            while stream.tell() - cursor < _MAX_FRAME:
                start = stream.tell()
                line = stream.readline(_MAX_FRAME + 1)
                if not line:
                    break
                if len(line) > _MAX_FRAME:
                    raise SandboxError("Runtime event exceeds its frame limit")
                if not line.endswith(b"\n"):
                    stream.seek(start)
                    break
                frames.append(json.loads(line))
            cursor = stream.tell()
            drained = not stream.read(1)
    else:
        if cursor:
            raise ValueError("Runtime journal has no such cursor")
        drained = True
    result = None
    if drained and result_ready:
        if result_path.stat().st_size > _MAX_RESULT:
            raise SandboxError("Runtime execution result exceeds its limit")
        result = json.loads(result_path.read_bytes())
    status = json.loads((directory / "status.json").read_bytes())
    if not result_path.exists():
        if status["phase"] == "running" and _process_start(status["pid"]) != status.get("start"):
            result = {
                "type": "execution_unknown",
                "error": "Runtime worker disappeared; reconcile effects before retrying",
            }
        elif status["phase"] == "starting" and time.time() - status["created_at"] > 30:
            result = {"type": "execution_unknown", "error": "Runtime dispatch outcome is unknown"}
    return {"version": _VERSION, "execution_id": execution_id, "cursor": cursor, "frames": frames, "result": result}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sandbox runtime protocol")
    parser.add_argument("operation", choices=("start", "poll", "worker"))
    parser.add_argument("directory", nargs="?")
    args = parser.parse_args()
    if args.operation == "worker":
        _worker(Path(args.directory))
        return
    request = json.loads(sys.stdin.buffer.read(_MAX_REQUEST + 1))
    root = Path(os.environ.get("AGNO_SANDBOX_RUNTIME_DIR", "/runtime"))
    result = (
        _start(root, request) if args.operation == "start" else _poll(root, request["execution_id"], request["cursor"])
    )
    print(_encode(result).decode())


if __name__ == "__main__":
    main()
