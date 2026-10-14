"""In-computer entrypoint for an Amazon Bedrock AgentCore Runtime sandbox image.

``serve`` is the container entrypoint and runs as root. It answers the AgentCore
HTTP contract on port 8080: GET /ping and POST /invocations. An invocation can
claim this microVM for one sandbox generation, describe the claim, forward a
runtime start or poll to the local runtime server, or stage command input.

``exec`` wraps every provider command. It refuses an unclaimed microVM, applies
the claimed environment and drops to UID/GID 1000 in /workspace, the same user
and directory the Docker sandbox uses.

AgentCore starts a new microVM whenever a stopped session is called again, so a
session id alone never proves which computer answers. The claim lives on this
microVM's own disk and dies with it. An unclaimed microVM is a replacement and
must not run work for the generation that preceded it.
"""

import ctypes
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

_CONTROL = Path("/var/lib/agno-control")
_CLAIM = _CONTROL / "claim.json"
_WORKSPACE, _RUNTIME = Path("/workspace"), Path("/runtime")
_PORT = 8080
_RUNTIME_PORT = 8765
_TOKEN_ENV = "AGNO_SANDBOX_RUNTIME_TOKEN"
_GUARD_EXIT = 125
_MAX_INPUT = 8 * 1024 * 1024
_USER = 1000

_lock = threading.Lock()
_state: Dict[str, Any] = {"token": None, "supervisor": None}
_ping = {"status": "Healthy", "since": int(time.time())}


def _control_dir() -> None:
    if os.geteuid() != 0:
        raise PermissionError("The AgentCore sandbox server must run as root")
    _CONTROL.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = _CONTROL.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise PermissionError("The control directory must belong to root alone")


def _write_private(path: Path, data: bytes) -> None:
    temporary = path.with_name("." + path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.write(descriptor, data)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


def _load_claim() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(_CLAIM.read_text())
    except FileNotFoundError:
        return None


def _drop_privileges() -> None:
    os.setgroups([])
    os.setgid(_USER)
    os.setuid(_USER)
    # PR_SET_NO_NEW_PRIVS: setuid binaries cannot take a command back to root.
    if ctypes.CDLL(None, use_errno=True).prctl(38, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Could not disable privilege elevation")


def _environment(claim: Dict[str, Any], **extra: str) -> Dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key != _TOKEN_ENV}
    environment.update(claim["env"])
    environment.update(HOME=str(_RUNTIME), **extra)
    return environment


def _expire(deadline: float) -> None:
    # AgentCore lifetimes are runtime-wide. Exiting the entrypoint bounds this
    # generation: AgentCore marks the microVM unhealthy and ends it.
    time.sleep(max(0.0, deadline - time.time()))
    os._exit(0)


def _start_runtime(claim: Dict[str, Any]) -> None:
    token = secrets.token_urlsafe(32)
    environment = _environment(claim, **{_TOKEN_ENV: token})
    _state["supervisor"] = subprocess.Popen(
        [sys.executable, "-I", "-m", "agno.sandbox.runtime", "supervise", "--port", str(_RUNTIME_PORT)],
        cwd=_WORKSPACE,
        env=environment,
        stdin=subprocess.DEVNULL,
        preexec_fn=_drop_privileges,
        start_new_session=True,
    )
    _state["token"] = token
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            status, _ = _forward("GET", "/health", None, timeout=2)
            if status == 200:
                return
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError("The sandbox runtime server did not become ready")


def _claim(request: Dict[str, Any]) -> Dict[str, Any]:
    metadata, env, lifetime = request.get("metadata"), request.get("env"), request.get("lifetime")
    if not isinstance(metadata, dict) or not all(isinstance(v, str) for v in metadata.values()):
        raise ValueError("Claim metadata must map strings to strings")
    if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ValueError("Claim environment must map strings to strings")
    if _TOKEN_ENV in env:
        raise ValueError("The runtime token is generated per computer; do not set it in env")
    if type(lifetime) is not int or lifetime < 60:
        raise ValueError("Claim lifetime must be at least 60 seconds")
    _control_dir()
    with _lock:
        existing = _load_claim()
        if existing is not None:
            if existing["metadata"] != metadata or existing["env"] != env:
                raise PermissionError("This computer is already claimed with a different identity")
            return {"metadata": existing["metadata"], "created": False}
        for path in (_WORKSPACE, _RUNTIME):
            path.mkdir(mode=0o700, exist_ok=True)
            os.chown(path, _USER, _USER)
            path.chmod(0o700)
        claim = {"metadata": metadata, "env": env, "deadline": time.time() + lifetime}
        _write_private(_CLAIM, json.dumps(claim).encode())
        _start_runtime(claim)
    threading.Thread(target=_expire, args=(claim["deadline"],), daemon=True).start()
    return {"metadata": metadata, "created": True}


def _describe(request: Dict[str, Any]) -> Dict[str, Any]:
    claim = _load_claim()
    if claim is None:
        return {"claimed": False}
    return {"claimed": True, "metadata": claim["metadata"]}


def _forward(method: str, path: str, body: Optional[bytes], *, timeout: float) -> Any:
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + str(_state["token"])}
    request = urllib.request.Request(
        f"http://127.0.0.1:{_RUNTIME_PORT}{path}", data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def _rpc(request: Dict[str, Any]) -> Dict[str, Any]:
    if _load_claim() is None or _state["token"] is None:
        raise PermissionError("Unclaimed computer")
    operation, payload = request.get("operation"), request.get("payload")
    if operation not in ("start", "poll") or not isinstance(payload, str):
        raise ValueError("Runtime RPC requires start/poll and a JSON payload")
    try:
        wait = float(json.loads(payload).get("wait", 0) or 0)
    except (ValueError, AttributeError):
        wait = 0.0
    status, body = _forward("POST", "/" + operation, payload.encode(), timeout=15 + min(max(wait, 0.0), 30.0))
    return {"status": status, "body": body}


def _stage(request: Dict[str, Any]) -> Dict[str, Any]:
    """Store command input that ``exec --stdin NAME`` hands to the command and deletes."""
    if _load_claim() is None:
        raise PermissionError("Unclaimed computer")
    name = request.get("name", "")
    if not re.fullmatch(r"[a-f0-9]{32}", name):
        raise ValueError("Invalid staged input name")
    data = bytes.fromhex(request.get("data", ""))
    if len(data) > _MAX_INPUT:
        raise ValueError("Staged input exceeds its limit")
    _write_private(_CONTROL / (name + ".stdin"), data)
    return {"size": len(data)}


def _busy() -> bool:
    """A runtime worker is alive for an unfinished job. A job orphaned by a lost
    process must not keep the session awake, so a status file alone does not count."""
    jobs = _RUNTIME / "jobs"
    if not jobs.is_dir():
        return False
    for job in jobs.iterdir():
        if (job / "result.json").exists():
            continue
        try:
            pid = json.loads((job / "status.json").read_text()).get("pid")
        except (OSError, ValueError):
            continue
        if isinstance(pid, int) and Path(f"/proc/{pid}").exists():
            return True
    return False


def _ping_reply() -> Dict[str, Any]:
    # time_of_last_update is when the status changed. Sending the current time on
    # every ping keeps AgentCore from ever treating the session as idle.
    status = "HealthyBusy" if _busy() else "Healthy"
    if status != _ping["status"]:
        _ping.update(status=status, since=int(time.time()))
    return {"status": status, "time_of_last_update": _ping["since"]}


_OPERATIONS = {"claim": _claim, "describe": _describe, "rpc": _rpc, "stage": _stage}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: Any) -> None:
        return

    def _reply(self, body: Dict[str, Any]) -> None:
        payload = json.dumps(body, allow_nan=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        self._reply(_ping_reply() if self.path == "/ping" else {"ok": False, "error": "Unknown path"})

    def do_POST(self) -> None:
        if self.path != "/invocations":
            self._reply({"ok": False, "error": "Unknown path"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 < length <= 3 * _MAX_INPUT:
                raise ValueError("Invocation body is empty or too large")
            request = json.loads(self.rfile.read(length))
            operation = _OPERATIONS[request.pop("op")]
            # Errors travel in the body: AgentCore turns a non-2xx agent reply into an
            # opaque service error that would hide the reason from the provider.
            self._reply({"ok": True, "value": operation(request)})
        except Exception as error:
            self._reply({"ok": False, "error": f"{type(error).__name__}: {error}"[:2000]})


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self) -> None:
        # Skip the stdlib's reverse DNS lookup of the bind address.
        import socketserver

        socketserver.TCPServer.server_bind(self)
        self.server_name = "agentcore-sandbox"
        self.server_port = self.server_address[1]


def _guarded_exec(arguments: List[str]) -> None:
    claim = _load_claim()
    if claim is None:
        sys.stderr.write("AgentCore computer is not claimed; refusing to run on replacement compute\n")
        sys.exit(_GUARD_EXIT)
    if arguments[:1] == ["--stdin"]:
        name, arguments = arguments[1], arguments[2:]
        if not re.fullmatch(r"[a-f0-9]{32}", name):
            sys.exit("Invalid staged input name")
        path = _CONTROL / (name + ".stdin")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        os.unlink(path)
        os.dup2(descriptor, 0)
        os.close(descriptor)
    if arguments[:1] != ["--"] or len(arguments) < 2:
        sys.exit("usage: exec [--stdin NAME] -- ARGV...")
    argv = arguments[1:]
    environment = _environment(claim)
    _drop_privileges()
    os.chdir(_WORKSPACE)
    os.execvpe(argv[0], argv, environment)


def main() -> None:
    if sys.argv[1:2] == ["serve"]:
        _Server(("0.0.0.0", _PORT), _Handler).serve_forever()
    elif sys.argv[1:2] == ["exec"]:
        _guarded_exec(sys.argv[2:])
    else:
        sys.exit("usage: python -I -m agno.sandbox.agentcore_server serve | exec [--stdin NAME] -- ARGV...")


if __name__ == "__main__":
    main()
