"""Portable checkpoint archives and immutable storage outside sandbox compute.

Callers must drain the harness and quiesce workspace writers before capture.
Filesystem checkpoints do not capture processes or undo external side effects.
"""

from __future__ import annotations

import asyncio
import errno
import hashlib
import io
import json
import os
import posixpath
import shutil
import stat
import tarfile
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, Dict, Mapping, Optional, Sequence, TypeVar

from agno.sandbox.base import SandboxError

_ROOTS = {"workspace", "native"}
_MANIFEST = "manifest.json"
_CHUNK = 1024 * 1024
_T = TypeVar("_T")


async def _drain(task: asyncio.Task[Any]) -> Optional[BaseException]:
    """Let a shielded operation finish, however often the caller is cancelled.

    Shielding alone is not enough: a second cancellation interrupts the await that was
    waiting for the work, and the caller returns while it is still running. ``wait``
    reports completion without re-raising, so the operation's own failure cannot divert
    the drain either. Returning the failure retrieves it, so it is never a stray task
    exception, and lets the caller chain it onto the cancellation it is about to raise.
    """
    while not task.done():
        with suppress(asyncio.CancelledError):
            await asyncio.wait({task})
    return None if task.cancelled() else task.exception()


async def _thread(function: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    # Filesystem work cannot be stopped by cancelling its awaiter. Drain it so the
    # caller never races cleanup/retry against a still-writing background thread.
    task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError as cancelled:
        failure = await _drain(task)
        if failure is None:
            raise
        # Cancellation stays the outcome, but the write that died under it is still the
        # useful diagnostic, so chain it on rather than discarding it.
        raise cancelled from failure


@dataclass(frozen=True)
class CheckpointRef:
    """Immutable bytes; publish this reference only after the durable run commit."""

    sha256: str
    size: int

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ValueError("Invalid checkpoint digest")
        if type(self.size) is not int or self.size < 1:
            raise ValueError("Checkpoint size must be positive")


@dataclass(frozen=True)
class CheckpointLimits:
    max_bytes: int = 1024 * 1024 * 1024
    max_entries: int = 100_000
    max_manifest_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if any(type(v) is not int or v < 1 for v in (self.max_bytes, self.max_entries, self.max_manifest_bytes)):
            raise ValueError("Checkpoint limits must be positive integers")


def _name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or "\x00" in name
        or path.is_absolute()
        or any(p in ("", ".", "..") for p in name.split("/"))
    ):
        raise SandboxError("Unsafe checkpoint path")
    if path.parts[0] not in _ROOTS and name != _MANIFEST:
        raise SandboxError("Checkpoint path is outside declared roots")
    return path


def _link(name: str, target: str) -> None:
    if not target or target.startswith("/") or "\\" in target or "\x00" in target:
        raise SandboxError("Unsafe checkpoint symlink")
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
    if PurePosixPath(resolved).parts[0] != PurePosixPath(name).parts[0]:
        raise SandboxError("Checkpoint symlink escapes its durable root")


def _resolved(path: Path) -> Path:
    """Resolve a symlink, rejecting a chain the kernel cannot follow.

    Python 3.13 stopped raising from ``resolve()`` for symlink loops, so ask for ELOOP;
    a dangling link reports ENOENT and keeps the unresolved path it points at.
    """
    try:
        os.stat(path)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise SandboxError("Checkpoint contains a symlink cycle or an unfollowable chain") from error
    return path.resolve()


def _regular(path: Path) -> BinaryIO:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise SandboxError("Checkpoint object must be a regular file")
    return os.fdopen(fd, "rb")


def _preflight(stream: BinaryIO, limits: CheckpointLimits) -> None:
    """Bound extension headers before tarfile allocates their payloads.

    Also requires the stream to reach its end-of-archive marker.
    """
    length = os.fstat(stream.fileno()).st_size
    offset, headers, extensions = 0, 0, 0
    while offset + 512 <= length:
        stream.seek(offset)
        header = stream.read(512)
        if header == b"\x00" * 512:
            stream.seek(0)
            return
        try:
            info = tarfile.TarInfo.frombuf(header, encoding="utf-8", errors="surrogateescape")
        except tarfile.TarError as error:
            raise SandboxError("Invalid checkpoint archive framing") from error
        headers += 1
        if info.size < 0 or offset + 512 + info.size > length or headers > limits.max_entries * 3:
            raise SandboxError("Invalid checkpoint archive framing")
        if info.type in (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK):
            extensions += info.size
            if info.size > limits.max_manifest_bytes or extensions > limits.max_manifest_bytes * 16:
                raise SandboxError("Checkpoint extension metadata exceeds its limit")
        offset += 512 + ((info.size + 511) // 512) * 512
    # Running out of bytes instead of reaching the end-of-archive marker means the stream
    # stopped early. A cut on a member boundary otherwise reads as a whole archive that
    # happens to hold fewer files, and its digest matches those bytes.
    raise SandboxError("Checkpoint archive ends without its end-of-archive marker")


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class CheckpointArchive:
    """Uncompressed tar with exactly workspace/native roots and a JSON state manifest.

    Native credentials must live outside the declared native root. Explicit
    exclusions are relative to either root, for example ``native/auth.json``.
    User workspace files, including ignored/untracked files, are otherwise kept.
    Restore rejects special files, hardlinks, escaping symlinks and duplicate paths.
    """

    def __init__(self, limits: CheckpointLimits = CheckpointLimits()) -> None:
        self.limits = limits

    def capture(
        self, roots: Mapping[str, Path], destination: Path, *, state: Mapping[str, Any], exclude: Sequence[str] = ()
    ) -> None:
        if set(roots) != _ROOTS:
            raise ValueError("Checkpoint requires workspace and native roots")
        exclusions = set(exclude)
        for item in exclusions:
            if str(_name(item)) == _MANIFEST or item in _ROOTS:
                raise ValueError("Cannot exclude a manifest or entire durable root")
        manifest = json.dumps(
            {"version": 1, "state": dict(state), "excluded": sorted(exclusions)}, allow_nan=False
        ).encode()
        if len(manifest) > self.limits.max_manifest_bytes:
            raise SandboxError("Checkpoint manifest exceeds its limit")
        count, size = 1, len(manifest)
        destination = Path(destination)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        root_paths = {name: Path(path).resolve() for name, path in roots.items()}
        for name, original in roots.items():
            if Path(original).is_symlink() or not root_paths[name].is_dir():
                raise SandboxError("Durable roots must be real directories")
            if destination.resolve().is_relative_to(root_paths[name]):
                raise SandboxError("Checkpoint destination cannot be inside a captured root")
        output_file = destination.open("xb")
        try:
            with (
                output_file as output,
                tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive,
            ):
                info = tarfile.TarInfo(_MANIFEST)
                info.size = len(manifest)
                info.mode = 0o600
                archive.addfile(info, io.BytesIO(manifest))

                def add(path: Path, name: str) -> None:
                    nonlocal count, size
                    if any(name == item or name.startswith(item + "/") for item in exclusions):
                        return
                    _name(name)
                    count += 1
                    if count > self.limits.max_entries:
                        raise SandboxError("Checkpoint has too many entries")
                    entry = path.lstat()
                    info = tarfile.TarInfo(name)
                    info.mode = entry.st_mode & 0o777
                    info.mtime = entry.st_mtime
                    if stat.S_ISREG(entry.st_mode):
                        info.type, info.size = tarfile.REGTYPE, entry.st_size
                    elif stat.S_ISDIR(entry.st_mode):
                        info.type = tarfile.DIRTYPE
                    elif stat.S_ISLNK(entry.st_mode):
                        info.type, info.linkname = tarfile.SYMTYPE, os.readlink(path)
                    else:
                        raise SandboxError("Checkpoint contains an unsupported file type")
                    if info.isdir():
                        archive.addfile(info)
                        for child in sorted(path.iterdir()):
                            add(child, name + "/" + child.name)
                    elif info.issym():
                        _link(name, info.linkname)
                        root = root_paths[PurePosixPath(name).parts[0]]
                        if not _resolved(path).is_relative_to(root):
                            raise SandboxError("Checkpoint symlink chain escapes its durable root")
                        archive.addfile(info)
                    elif info.isfile():
                        size += info.size
                        if size > self.limits.max_bytes:
                            raise SandboxError("Checkpoint data exceeds its limit")
                        with _regular(path) as source:
                            before = os.fstat(source.fileno())
                            if (before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns) != (
                                entry.st_ino,
                                entry.st_dev,
                                entry.st_size,
                                entry.st_mtime_ns,
                            ):
                                raise SandboxError("Workspace changed during checkpoint capture")
                            archive.addfile(info, source)
                            after = os.fstat(source.fileno())
                            if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                                after.st_size,
                                after.st_mtime_ns,
                                after.st_ino,
                            ) or before.st_size != info.size:
                                raise SandboxError("Workspace changed during checkpoint capture")
                    else:
                        raise SandboxError("Checkpoint contains an unsupported file type")
                    if output.tell() > self.limits.max_bytes:
                        raise SandboxError("Checkpoint archive exceeds its limit")

                for name in sorted(_ROOTS):
                    add(root_paths[name], name)
            if destination.stat().st_size > self.limits.max_bytes:
                raise SandboxError("Checkpoint archive exceeds its limit")
        except BaseException:
            destination.unlink(missing_ok=True)
            raise

    async def acapture(
        self, roots: Mapping[str, Path], destination: Path, *, state: Mapping[str, Any], exclude: Sequence[str] = ()
    ) -> None:
        await _thread(self.capture, roots, destination, state=state, exclude=exclude)

    def restore(self, source: Path, destination: Path) -> Dict[str, Any]:
        """Restore into a new directory; failure never exposes a partial destination.

        The parent directory is trusted coordinator-owned storage. It must not be
        writable by sandbox processes or concurrent callers targeting this path.
        """
        source, destination = Path(source), Path(destination)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        # Resolved once: the symlink check below resolves each materialized link, so a
        # symlink anywhere in the parent's own path would otherwise fail every comparison.
        temporary = Path(tempfile.mkdtemp(prefix=".restore-", dir=destination.parent)).resolve()
        try:
            with _regular(source) as stream:
                if os.fstat(stream.fileno()).st_size > self.limits.max_bytes:
                    raise SandboxError("Checkpoint archive exceeds its limit")
                _preflight(stream, self.limits)
                with tarfile.open(fileobj=stream, mode="r:") as archive:
                    members: Dict[str, tarfile.TarInfo] = {}
                    total = 0
                    for member in archive:
                        _name(member.name)
                        if member.name in members:
                            raise SandboxError("Duplicate checkpoint path")
                        if not (member.isdir() or member.isfile() or member.issym()) or member.sparse is not None:
                            raise SandboxError("Checkpoint contains an unsupported file type")
                        if member.size < 0 or (not member.isfile() and member.size != 0):
                            raise SandboxError("Invalid checkpoint member size")
                        if member.issym():
                            _link(member.name, member.linkname)
                        total += member.size
                        members[member.name] = member
                        if total > self.limits.max_bytes or len(members) > self.limits.max_entries:
                            raise SandboxError("Checkpoint exceeds restore limits")
                    if any(root not in members or not members[root].isdir() for root in _ROOTS):
                        raise SandboxError("Checkpoint is missing durable roots")
                    for name in members:
                        for parent in PurePosixPath(name).parents:
                            if str(parent) != "." and (str(parent) not in members or not members[str(parent)].isdir()):
                                raise SandboxError("Checkpoint parent is not a declared directory")
                    manifest_info = members.get(_MANIFEST)
                    if (
                        manifest_info is None
                        or not manifest_info.isfile()
                        or manifest_info.size > self.limits.max_manifest_bytes
                    ):
                        raise SandboxError("Invalid checkpoint manifest")
                    manifest_file = archive.extractfile(manifest_info)
                    assert manifest_file is not None
                    try:
                        manifest = json.load(manifest_file)
                    except (json.JSONDecodeError, UnicodeDecodeError) as error:
                        raise SandboxError("Invalid checkpoint manifest") from error
                    if (
                        not isinstance(manifest, dict)
                        or manifest.get("version") != 1
                        or not isinstance(manifest.get("state"), dict)
                    ):
                        raise SandboxError("Unsupported checkpoint manifest")
                    # No extractall: validate the entire member graph before creating paths.
                    for name, member in sorted(
                        members.items(), key=lambda item: (len(PurePosixPath(item[0]).parts), item[0])
                    ):
                        if name == _MANIFEST:
                            continue
                        path = temporary / name
                        if member.isdir():
                            path.mkdir(mode=0o700)
                        elif member.issym():
                            path.symlink_to(member.linkname)
                        else:
                            extracted = archive.extractfile(member)
                            assert extracted is not None
                            with path.open("xb") as output:
                                shutil.copyfileobj(extracted, output, _CHUNK)
                            path.chmod(member.mode & 0o777)
                    for name, member in members.items():
                        if member.issym():
                            root = temporary / PurePosixPath(name).parts[0]
                            if not _resolved(temporary / name).is_relative_to(root):
                                raise SandboxError("Checkpoint symlink chain escapes its durable root")
                    # Directories remain writable while children are materialized.
                    for name, member in sorted(members.items(), reverse=True):
                        if member.isdir():
                            (temporary / name).chmod(member.mode & 0o777)
            os.rename(temporary, destination)
            return manifest["state"]
        except tarfile.TarError as error:
            # Scoped by type, not by block: only the tarfile calls above can raise it,
            # namely opening the archive, walking members and reading a member's bytes.
            raise SandboxError("Invalid checkpoint archive") from error
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    async def arestore(self, source: Path, destination: Path) -> Dict[str, Any]:
        return await _thread(self.restore, source, destination)


class FileCheckpointStore:
    """Content-addressed immutable objects on trusted shared durable storage.

    A service-host local disk does not cover host loss. Production callers must
    choose storage whose replication/durability matches their recovery promise.
    Objects are unreachable until a database transaction publishes their reference.
    Deletion/retention is intentionally separate from compute destruction.
    """

    def __init__(self, root: Path, *, max_bytes: int = 1024 * 1024 * 1024) -> None:
        self.root = Path(root)
        if self.root.is_symlink():
            raise ValueError("Checkpoint store root cannot be a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("Checkpoint object limit must be positive")
        self.max_bytes = max_bytes

    def put(self, source: Path) -> CheckpointRef:
        fd, name = tempfile.mkstemp(prefix=".upload-", dir=self.root)
        temporary = Path(name)
        try:
            digest, size = hashlib.sha256(), 0
            with os.fdopen(fd, "wb") as output, _regular(Path(source)) as stream:
                while chunk := stream.read(_CHUNK):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise SandboxError("Checkpoint object exceeds its limit")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            reference = CheckpointRef(digest.hexdigest(), size)
            target = self.root / reference.sha256
            try:
                os.link(temporary, target)
            except FileExistsError:
                self.verify(reference)
            _fsync_directory(self.root)
            return reference
        finally:
            temporary.unlink(missing_ok=True)

    async def aput(self, source: Path) -> CheckpointRef:
        return await _thread(self.put, source)

    def verify(self, reference: CheckpointRef) -> Path:
        if reference.size > self.max_bytes:
            raise SandboxError("Checkpoint object exceeds its limit")
        path = self.root / reference.sha256
        digest, size = hashlib.sha256(), 0
        with _regular(path) as stream:
            if os.fstat(stream.fileno()).st_size != reference.size:
                raise SandboxError("Checkpoint size mismatch")
            while chunk := stream.read(_CHUNK):
                size += len(chunk)
                if size > reference.size:
                    raise SandboxError("Checkpoint object changed while reading")
                digest.update(chunk)
        if size != reference.size or digest.hexdigest() != reference.sha256:
            raise SandboxError("Checkpoint checksum mismatch")
        return path

    async def averify(self, reference: CheckpointRef) -> Path:
        return await _thread(self.verify, reference)

    def restore(
        self, reference: CheckpointRef, destination: Path, *, archive: CheckpointArchive | None = None
    ) -> Dict[str, Any]:
        # The store is coordinator-owned and immutable. Sandboxes never mount it.
        return (archive or CheckpointArchive()).restore(self.verify(reference), destination)

    async def arestore(
        self, reference: CheckpointRef, destination: Path, *, archive: CheckpointArchive | None = None
    ) -> Dict[str, Any]:
        return await _thread(self.restore, reference, destination, archive=archive)
