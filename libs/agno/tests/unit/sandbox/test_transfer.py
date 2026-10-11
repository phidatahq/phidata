import io
import json
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from agno.sandbox import SandboxError, SandboxHandle
from agno.sandbox.checkpoint import CheckpointArchive, FileCheckpointStore
from agno.sandbox.docker import DockerSandboxProvider
from agno.sandbox.transfer import DEFAULT_NATIVE_EXCLUSIONS, DockerCheckpointTransfer


def exported(path, root, entries):
    with tarfile.open(path, "w") as archive:
        info = tarfile.TarInfo(root)
        info.type = tarfile.DIRTYPE
        info.mode = 0o700
        archive.addfile(info)
        for name, kind, value in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.mode = 0o700 if kind == tarfile.DIRTYPE else 0o600
            if kind == tarfile.REGTYPE:
                info.size = len(value)
                archive.addfile(info, io.BytesIO(value))
            else:
                info.linkname = value
                archive.addfile(info)


def test_combine_converts_hardlinks_and_excludes_native_credentials(tmp_path):
    exported(
        tmp_path / "workspace.tar",
        "workspace",
        [("workspace/file", tarfile.REGTYPE, b"data"), ("workspace/link", tarfile.LNKTYPE, "workspace/file")],
    )
    exported(
        tmp_path / "native.tar",
        "native",
        [
            ("native/codex", tarfile.DIRTYPE, ""),
            ("native/codex/auth.json", tarfile.REGTYPE, b"secret"),
            ("native/codex/thread", tarfile.REGTYPE, b"state"),
        ],
    )
    transfer = DockerCheckpointTransfer(DockerSandboxProvider("test"), FileCheckpointStore(tmp_path / "objects"))
    transfer._combine(
        {"workspace": tmp_path / "workspace.tar", "native": tmp_path / "native.tar"},
        tmp_path / "result.tar",
        {"run": "r"},
        DEFAULT_NATIVE_EXCLUSIONS,
    )
    assert CheckpointArchive().validate(tmp_path / "result.tar") == {"run": "r"}
    CheckpointArchive().restore(tmp_path / "result.tar", tmp_path / "restored")
    assert (tmp_path / "restored/workspace/link").read_bytes() == b"data"
    assert not (tmp_path / "restored/native/codex/auth.json").exists()
    transfer._export_root(tmp_path / "result.tar", "workspace", tmp_path / "import.tar")
    with tarfile.open(tmp_path / "import.tar") as archive:
        assert archive.getnames() == ["file", "link"]
        assert all(member.uid == member.gid == 1000 for member in archive)


def test_capture_combine_rejects_wrong_export_root(tmp_path):
    exported(tmp_path / "workspace.tar", "other", [])
    transfer = DockerCheckpointTransfer(DockerSandboxProvider("test"), FileCheckpointStore(tmp_path / "objects"))
    with pytest.raises(SandboxError):
        transfer._combine({"workspace": tmp_path / "workspace.tar"}, tmp_path / "result.tar", {}, [])


def test_validate_checks_composed_links_without_creating_files(tmp_path, monkeypatch):
    source = tmp_path / "checkpoint.tar"
    with tarfile.open(source, "w") as archive:
        payload = b'{"version":1,"state":{}}'
        info = tarfile.TarInfo("manifest.json")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
        for root in ("workspace", "native"):
            info = tarfile.TarInfo(root)
            info.type = tarfile.DIRTYPE
            archive.addfile(info)
        for name, target in (("workspace/a", "."), ("workspace/b", "a/../native")):
            info = tarfile.TarInfo(name)
            info.type, info.linkname = tarfile.SYMTYPE, target
            archive.addfile(info)
    monkeypatch.setattr(Path, "mkdir", lambda *a, **kw: pytest.fail("Validation must not extract files"))
    with pytest.raises(SandboxError, match="chain escapes"):
        CheckpointArchive().validate(source)


@pytest.mark.asyncio
async def test_namespace_tmpfs_is_rejected_before_capture(tmp_path):
    provider = DockerSandboxProvider("test")
    handle = SandboxHandle("id", "name", "a", "s", 1, "running", "digest")
    provider._owned = AsyncMock(return_value=handle)
    provider._docker = AsyncMock(return_value=(0, json.dumps([{"Mounts": []}]).encode(), b""))
    transfer = DockerCheckpointTransfer(provider, FileCheckpointStore(tmp_path / "objects"))
    with pytest.raises(SandboxError, match="checkpointable"):
        await transfer.acapture(handle, state={})
    assert provider._docker.call_count == 1


@pytest.mark.asyncio
async def test_lost_pause_response_resumes_before_reporting_failure(tmp_path):
    provider = DockerSandboxProvider("test")
    running = SandboxHandle("id", "name", "a", "s", 1, "running", "digest")
    paused = SandboxHandle("id", "name", "a", "s", 1, "paused", "digest")
    provider._owned = AsyncMock(side_effect=[running, paused, running])
    provider._docker = AsyncMock(side_effect=[TimeoutError("lost pause"), (0, b"", b"")])
    transfer = DockerCheckpointTransfer(provider, FileCheckpointStore(tmp_path / "objects"))
    with pytest.raises(TimeoutError, match="lost pause"):
        await transfer._pause(running)
    assert provider._docker.call_args.args == ("container", "unpause", "id")
