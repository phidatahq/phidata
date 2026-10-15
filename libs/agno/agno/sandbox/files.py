"""Bounded text inputs and outputs for a sandbox execution workspace."""

import os
import shutil
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict

_MAX_BYTES = 250_000
_MAX_FILES = 100


def _path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 1000 or "\\" in value:
        raise ValueError("Workspace files require bounded relative paths")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in (".", "..") for part in path.parts)
        or len(path.parts) > 20
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError("Workspace files require canonical relative paths")
    return value


def validate_files(value: Any) -> Dict[str, str]:
    """Validate text inputs before submission and again inside the runtime."""
    if not isinstance(value, dict) or len(value) > _MAX_FILES:
        raise ValueError("Workspace inputs must contain at most 100 text files")
    total = 0
    for path, content in value.items():
        _path(path)
        if not isinstance(content, str):
            raise ValueError("Workspace file content must be text")
        total += len(content.encode("utf-8"))
        if total > _MAX_BYTES:
            raise ValueError("Workspace files exceed 250 KB")
    return dict(value)


def _prepare(value: Any, workspace: Path) -> None:
    files = validate_files(value)
    target = workspace / "context"
    output = workspace / "output"
    if target.is_symlink() or output.is_symlink():
        raise ValueError("Workspace context and output must not be symlinks")
    staging = Path(tempfile.mkdtemp(prefix=".context-", dir=workspace))
    try:
        for path, content in files.items():
            destination = staging / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(content)
            destination.chmod(0o444)
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
        output.mkdir(exist_ok=True)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _outputs(workspace: Path) -> Dict[str, str]:
    """Read only regular, bounded text files without following links or parent races."""
    result: Dict[str, str] = {}
    total = 0

    def visit(directory: int, prefix: str = "") -> None:
        nonlocal total
        with os.scandir(directory) as entries:
            for entry in entries:
                path = _path(prefix + entry.name)
                if entry.is_dir(follow_symlinks=False):
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try:
                        visit(child, path + "/")
                    finally:
                        os.close(child)
                    continue
                if len(result) >= _MAX_FILES:
                    raise ValueError("Sandbox produced too many output files")
                descriptor = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                try:
                    info = os.fstat(descriptor)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > _MAX_BYTES - total:
                        raise ValueError("Sandbox outputs must be bounded regular text files without links")
                    with os.fdopen(descriptor, "rb", closefd=False) as stream:
                        content = stream.read(_MAX_BYTES - total + 1)
                    total += len(content)
                    if total > _MAX_BYTES:
                        raise ValueError("Sandbox outputs exceed 250 KB")
                    result[path] = content.decode("utf-8")
                finally:
                    os.close(descriptor)

    try:
        root = os.open(workspace / "output", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return result
    try:
        visit(root)
    finally:
        os.close(root)
    return result
