"""Root-owned transport helper for prepared, trusted Linux sandbox images.

The transport runs as root; harnesses and commands always run as UID/GID 1000
with privilege elevation disabled. Root provider daemons must not write managed
roots. Capturing freezes that user until the computer is destroyed. This is a
filesystem checkpoint, not an application-consistent database backup.
"""

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import time
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from agno.sandbox.base import SandboxError
from agno.sandbox.checkpoint import CheckpointArchive, CheckpointLimits

_CONTROL = Path("/var/lib/agno-control")
_MAX_REQUEST = 1024 * 1024


def _control() -> None:
    if os.geteuid() != 0:
        raise SandboxError("Hosted transport requires root; commands drop privileges before execution")
    for parent in (Path("/var"), Path("/var/lib")):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise SandboxError("Transport directory has an unsafe parent")
    _CONTROL.mkdir(mode=0o700, exist_ok=True)
    info = _CONTROL.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise SandboxError("Transport directory must be owned exclusively by root")


def _path(name: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}\.(json|tar)", name):
        raise ValueError("Invalid transport object name")
    return _CONTROL / name


def _read(name: str, limit: int) -> bytes:
    path = _path(name)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_size > limit:
            raise SandboxError("Invalid transport object")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            value = stream.read(limit + 1)
        if len(value) > limit:
            raise SandboxError("Transport object exceeds its limit")
        return value
    finally:
        os.close(descriptor)


def _drop() -> None:
    if (_CONTROL / "frozen").exists():
        raise SandboxError("Captured compute cannot execute again; replace it from its checkpoint")
    os.setgroups([])
    os.setgid(1000)
    os.setuid(1000)
    # Linux PR_SET_NO_NEW_PRIVS: setuid binaries and file capabilities cannot
    # turn a user command back into a root checkpoint writer.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Could not disable privilege elevation")
    os.chdir("/workspace")
    os.environ["HOME"] = "/runtime/native"
    os.environ["CODEX_HOME"] = "/runtime/native/codex"


def _initialize() -> Dict[str, Any]:
    marker = _CONTROL / "initialized"
    if marker.exists():
        return {"initialized": True}
    for path in (Path("/workspace"), Path("/runtime")):
        if path.exists() or path.is_symlink():
            if not stat.S_ISDIR(path.lstat().st_mode) or any(path.iterdir()):
                raise SandboxError("Hosted runtime requires empty managed directories in the prepared image")
        else:
            path.mkdir(mode=0o700)
        path.chmod(0o700)
        os.chown(path, 1000, 1000)
    Path("/runtime/native").mkdir(mode=0o700)
    os.chown("/runtime/native", 1000, 1000)
    marker.write_text("1")
    return {"initialized": True}


def _freeze() -> None:
    (_CONTROL / "frozen").touch(mode=0o600)
    deadline = time.monotonic() + 10
    stable = 0
    while time.monotonic() < deadline:
        running = False
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = dict(line.split(":", 1) for line in (entry / "status").read_text().splitlines() if ":" in line)
                if "1000" not in fields.get("Uid", "").split():
                    continue
                state = fields["State"].strip().split()[0]
                if state not in ("T", "t", "Z", "X"):
                    running = True
                    os.kill(int(entry.name), signal.SIGSTOP)
            except (FileNotFoundError, ProcessLookupError):
                continue
        stable = 0 if running else stable + 1
        if stable == 3:
            return
        time.sleep(0.02)
    raise SandboxError("Could not freeze all managed filesystem writers")


def _capture(request: Dict[str, Any]) -> Dict[str, Any]:
    archive = CheckpointArchive(CheckpointLimits(**request["limits"]))
    _freeze()
    path = _path(request["object"])
    archive.capture(
        {"workspace": Path("/workspace"), "native": Path("/runtime/native")},
        path,
        state=request["state"],
        exclude=request["exclude"],
    )
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size": path.stat().st_size}


def _restore(request: Dict[str, Any]) -> Dict[str, Any]:
    if (_CONTROL / "used").exists() or (_CONTROL / "frozen").exists():
        raise SandboxError("Restore requires an unused computer")
    # Even a failed or interrupted import consumes this computer. The service
    # stops it instead of letting a later turn observe partially restored roots.
    (_CONTROL / "used").touch(mode=0o600)
    roots = (Path("/workspace"), Path("/runtime/native"))
    for path in roots:
        if not stat.S_ISDIR(path.lstat().st_mode) or any(path.iterdir()):
            raise SandboxError("Restore requires empty managed roots")
    source = _path(request["object"])
    limits = CheckpointLimits(**request["limits"])
    payload = _read(request["object"], limits.max_bytes)
    if len(payload) != request["size"] or hashlib.sha256(payload).hexdigest() != request["sha256"]:
        raise SandboxError("Uploaded checkpoint digest mismatch")
    del payload
    destination = _CONTROL / uuid4().hex
    archive = CheckpointArchive(limits)
    try:
        state = archive.restore(source, destination)
        for root, target in zip(("workspace", "native"), roots):
            restored = destination / root
            for directory, dirs, files in os.walk(restored, followlinks=False):
                os.chown(directory, 1000, 1000, follow_symlinks=False)
                for name in dirs + files:
                    os.chown(Path(directory) / name, 1000, 1000, follow_symlinks=False)
            target.rmdir()
            os.rename(restored, target)
        return {"state": state}
    finally:
        shutil.rmtree(destination, ignore_errors=True)
        source.unlink(missing_ok=True)


def _dispatch(operation: str, request: Dict[str, Any]) -> Dict[str, Any]:
    if operation == "init":
        return _initialize()
    if not (_CONTROL / "initialized").exists():
        raise SandboxError("Hosted runtime is not initialized")
    if operation == "capture":
        return _capture(request)
    if operation == "restore":
        return _restore(request)
    if operation == "remove":
        _path(request["object"]).unlink(missing_ok=True)
        return {}
    if operation not in ("exec", "start", "poll"):
        raise ValueError("Unsupported hosted operation")
    (_CONTROL / "used").touch(mode=0o600)
    _drop()
    if operation == "exec":
        from agno.sandbox._exec import _execute

        return _execute(request)
    from agno.sandbox.runtime import _poll, _start

    return (
        _start(Path("/runtime"), request)
        if operation == "start"
        else _poll(Path("/runtime"), request["execution_id"], request["cursor"])
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Hosted sandbox control transport")
    parser.add_argument("operation", choices=("init", "exec", "start", "poll", "capture", "restore", "remove"))
    parser.add_argument("request", nargs="?")
    args = parser.parse_args()
    _control()
    request = {}
    if args.request is not None:
        request = json.loads(_read(args.request, _MAX_REQUEST))
        _path(args.request).unlink()
    print(json.dumps(_dispatch(args.operation, request), allow_nan=False))


if __name__ == "__main__":
    main()
