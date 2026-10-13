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
import math
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from agno.sandbox.base import SandboxError

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


def _validate(request: Dict[str, Any]) -> None:
    if type(request.get("version")) is not int or request["version"] != _VERSION:
        raise ValueError("Unsupported runtime protocol version")
    for key in ("execution_id", "run_id", "session_id", "agent_id"):
        if not isinstance(request.get(key), str) or not request[key] or len(request[key]) > 256:
            raise ValueError("Runtime requires bounded string identities")
    if request.get("sdk") not in ("claude", "codex", "fixture"):
        raise ValueError("Unsupported runtime SDK")
    if not isinstance(request.get("input"), str) or not isinstance(request.get("config", {}), dict):
        raise ValueError("Runtime input must be text and configuration must be JSON")
    if request["sdk"] == "fixture" and os.environ.get("AGNO_SANDBOX_TEST_RUNTIME") != "1":
        raise ValueError("The fixture runtime is disabled")
    if {"db", "cwd", "id", "retries", "env", "client_options", "options", "keep_uploads"} & set(
        request.get("config", {})
    ):
        raise ValueError("Runtime owns database, workspace, identity, process environment and retry configuration")
    timeout = request.get("execution_timeout", 900)
    if not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise ValueError("Runtime execution timeout must be between 0 and 86400 seconds")
    if len(_encode(request)) > _MAX_REQUEST:
        raise ValueError("Runtime request exceeds its limit")


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
            "status": "COMPLETED",
            "content": request["input"],
        },
        "session": {"session_id": request["session_id"], "session_data": {"fixture": True}},
    }


def _agent(request: Dict[str, Any], native: Path) -> Any:
    from agno.db.sqlite import SqliteDb

    # This local database is native runtime state, not the authoritative service
    # database. It has no network credentials and is checkpointed after SDK drain.
    db = SqliteDb(db_file=str(native / "history.db"))
    config = dict(request.get("config", {}))
    config.update(id=request["agent_id"], cwd="/workspace", db=db, retries=0, keep_uploads=True)
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
    os.environ["CODEX_HOME"] = str(native / "codex")
    agent = _agent(request, native)
    run = None
    try:
        async for event in agent.arun(
            request["input"],
            run_id=request["run_id"],
            session_id=request["session_id"],
            user_id=request.get("user_id"),
            stream=True,
            stream_events=True,
            yield_run_output=True,
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


_MAX_WAIT = 30.0


def _poll_wait(root: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    """Poll, holding the request open until there is something to return.

    ``wait`` seconds of long-polling inside the container replaces a tight loop of
    requests from the host: the reply goes out as soon as new journal bytes or the
    result exist, and an idle page costs one request per ``wait`` instead of many.
    """
    wait = request.get("wait", 0)
    if not isinstance(wait, (int, float)) or not math.isfinite(wait) or wait < 0:
        raise ValueError("Runtime poll wait must be a nonnegative number of seconds")
    deadline = time.monotonic() + min(float(wait), _MAX_WAIT)
    while True:
        page = _poll(root, request["execution_id"], request["cursor"])
        if page["frames"] or page["result"] is not None or time.monotonic() >= deadline:
            return page
        time.sleep(0.05)


def _serve(root: Path, port: int, token: Optional[str] = None) -> Any:
    """The runtime as a small HTTP server, run as the container's entrypoint.

    POST /start and POST /poll take the same JSON as the stdin operations and return
    the same JSON; GET /health answers once the server is up. The journal, locks and
    worker are unchanged: this only replaces a process spawn per request with a
    pooled connection, which is what keeps the Docker daemon out of the hot path.

    With a token, every request must carry it as a bearer credential. The provider
    generates one per container and hands it to the coordinator with the handle, so
    a port reachable beyond the host's loopback (a shared daemon, a hosted provider)
    answers only its owner. The agent inside the container can already write the
    journal, so the server grants it nothing new either way.
    """
    import hmac
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    expected = ("Bearer " + token).encode() if token else None

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        # Headers and body go out as two small writes; without TCP_NODELAY the second waits on
        # the peer's delayed ACK, which turns a millisecond poll into a forty millisecond one.
        disable_nagle_algorithm = True

        def log_message(self, *args: Any) -> None:
            return

        def _authorized(self) -> bool:
            if expected is None:
                return True
            presented = (self.headers.get("Authorization") or "").encode()
            if hmac.compare_digest(presented, expected):
                return True
            self._reply(401, {"error": "Runtime request is missing or carries the wrong token"})
            return False

        def _reply(self, status: int, body: Dict[str, Any]) -> None:
            payload = _encode(body)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            if not self._authorized():
                return
            if self.path == "/health":
                self._reply(200, {"version": _VERSION, "ok": True})
            else:
                self._reply(404, {"error": "Unknown runtime operation"})

        def do_POST(self) -> None:
            if not self._authorized():
                return
            if self.path not in ("/start", "/poll"):
                self._reply(404, {"error": "Unknown runtime operation"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > _MAX_REQUEST:
                self._reply(413, {"error": "Runtime request exceeds its limit"})
                return
            try:
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise ValueError("Runtime request must be a JSON object")
                result = _start(root, request) if self.path == "/start" else _poll_wait(root, request)
            except (ValueError, KeyError, TypeError) as error:
                self._reply(400, {"error": str(error) or type(error).__name__})
            except SandboxError as error:
                self._reply(409, {"error": str(error)})
            except Exception as error:
                self._reply(500, {"error": (str(error) or type(error).__name__)[:2000]})
            else:
                self._reply(200, result)

    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def server_bind(self) -> None:
            # The stdlib resolves the bind address's FQDN here, a reverse DNS lookup that can
            # stall for seconds in a container with no resolver. The name is never used.
            import socketserver

            socketserver.TCPServer.server_bind(self)
            self.server_name = "sandbox-runtime"
            self.server_port = self.server_address[1]

    return Server(("0.0.0.0", port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sandbox runtime protocol")
    parser.add_argument("operation", choices=("start", "poll", "worker", "serve"))
    parser.add_argument("directory", nargs="?")
    parser.add_argument("--port", type=int, default=int(os.environ.get("AGNO_SANDBOX_RUNTIME_PORT", "8765")))
    args = parser.parse_args()
    root = Path(os.environ.get("AGNO_SANDBOX_RUNTIME_DIR", "/runtime"))
    if args.operation == "worker":
        _worker(Path(args.directory))
        return
    if args.operation == "serve":
        # The token comes from the environment, never the command line, so it stays out of ps.
        _serve(root, args.port, os.environ.get("AGNO_SANDBOX_RUNTIME_TOKEN") or None).serve_forever()
        return
    request = json.loads(sys.stdin.buffer.read(_MAX_REQUEST + 1))
    result = _start(root, request) if args.operation == "start" else _poll_wait(root, request)
    print(_encode(result).decode())


if __name__ == "__main__":
    main()
