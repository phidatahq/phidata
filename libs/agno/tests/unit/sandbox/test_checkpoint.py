import asyncio
import hashlib
import io
import json
import os
import tarfile
import threading
from pathlib import Path

import pytest

from agno.sandbox import SandboxError
from agno.sandbox.checkpoint import CheckpointArchive, CheckpointLimits, CheckpointRef, FileCheckpointStore


@pytest.fixture
def roots(tmp_path):
    paths = {name: tmp_path / name for name in ("workspace", "native")}
    for path in paths.values():
        path.mkdir()
    (paths["workspace"] / "tracked.py").write_text("print('hello')")
    (paths["workspace"] / ".gitignore").write_text("ignored\n")
    (paths["workspace"] / "ignored").write_bytes(b"ignored data")
    (paths["workspace"] / "untracked").write_bytes(bytes(range(256)))
    (paths["native"] / "transcript.jsonl").write_text('{"message":"remember this"}\n')
    (paths["native"] / "auth.json").write_text("credential")
    (paths["workspace"] / "link").symlink_to("tracked.py")
    (paths["workspace"] / "tracked.py").chmod(0o751)
    return paths


def capture(tmp_path, roots):
    archive = tmp_path / "checkpoint.tar"
    CheckpointArchive().capture(
        roots, archive, state={"run_id": "r", "native_id": "n", "conversation": ["hello"]}, exclude=["native/auth.json"]
    )
    return archive


def test_capture_store_restore_preserves_all_declared_files(tmp_path, roots):
    source = capture(tmp_path, roots)
    store = FileCheckpointStore(tmp_path / "objects")
    reference = store.put(source)
    assert reference == store.put(source)
    destination = tmp_path / "restored"
    state = store.restore(reference, destination)
    assert state == {"run_id": "r", "native_id": "n", "conversation": ["hello"]}
    assert (destination / "workspace/untracked").read_bytes() == bytes(range(256))
    assert (destination / "workspace/ignored").read_text() == "ignored data"
    assert (destination / "workspace/link").is_symlink()
    assert (destination / "workspace/link").read_text() == "print('hello')"
    assert (destination / "workspace/tracked.py").stat().st_mode & 0o777 == 0o751
    assert not (destination / "native/auth.json").exists()
    assert len(list(store.root.iterdir())) == 1


def test_hardlinked_source_files_are_copied_as_regular_bytes(tmp_path, roots):
    os.link(roots["workspace"] / "tracked.py", roots["workspace"] / "hardlink")
    source = capture(tmp_path, roots)
    CheckpointArchive().restore(source, tmp_path / "restored")
    assert (tmp_path / "restored/workspace/hardlink").read_text() == "print('hello')"


def test_failed_capture_removes_partial_archive(tmp_path, roots):
    (roots["workspace"] / "outside").symlink_to("/etc/passwd")
    with pytest.raises(SandboxError, match="symlink"):
        capture(tmp_path, roots)
    assert not (tmp_path / "checkpoint.tar").exists()


def test_capture_does_not_remove_an_existing_destination(tmp_path, roots):
    path = tmp_path / "checkpoint.tar"
    path.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        capture(tmp_path, roots)
    assert path.read_bytes() == b"existing"


def test_capture_must_not_include_itself(tmp_path, roots):
    with pytest.raises(SandboxError, match="inside"):
        CheckpointArchive().capture(roots, roots["workspace"] / "checkpoint.tar", state={})


def test_capture_limits_cleanup_partial_files(tmp_path, roots):
    archive = CheckpointArchive(CheckpointLimits(max_bytes=100))
    with pytest.raises(SandboxError, match="limit"):
        archive.capture(roots, tmp_path / "limited.tar", state={})
    assert not (tmp_path / "limited.tar").exists()


def test_corrupt_or_missing_object_is_not_restored(tmp_path, roots):
    store = FileCheckpointStore(tmp_path / "objects")
    reference = store.put(capture(tmp_path, roots))
    path = store.verify(reference)
    with path.open("r+b") as stream:
        stream.write(b"corrupt")
    with pytest.raises(SandboxError, match="checksum"):
        store.restore(reference, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
    path.unlink()
    with pytest.raises(FileNotFoundError):
        store.verify(reference)


def test_object_size_and_upload_cleanup(tmp_path, roots):
    store = FileCheckpointStore(tmp_path / "objects", max_bytes=10)
    with pytest.raises(SandboxError, match="limit"):
        store.put(capture(tmp_path, roots))
    assert list(store.root.iterdir()) == []


def test_existing_corrupt_object_is_not_overwritten(tmp_path, roots):
    source = capture(tmp_path, roots)
    store = FileCheckpointStore(tmp_path / "objects")
    reference = store.put(source)
    path = store.root / reference.sha256
    path.write_bytes(b"corrupt")
    with pytest.raises(SandboxError, match="size"):
        store.put(source)
    assert path.read_bytes() == b"corrupt"
    assert not list(store.root.glob(".upload-*"))


def malicious_archive(tmp_path, members):
    path = tmp_path / "malicious.tar"
    with tarfile.open(path, "w") as archive:
        manifest = json.dumps({"version": 1, "state": {}}).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest)
        archive.addfile(info, io.BytesIO(manifest))
        for root in ("workspace", "native"):
            info = tarfile.TarInfo(root)
            info.type = tarfile.DIRTYPE
            archive.addfile(info)
        for name, kind, target in members:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.linkname = target
            if kind == tarfile.REGTYPE:
                info.size = 1
                archive.addfile(info, io.BytesIO(b"x"))
            else:
                archive.addfile(info)
    return path


@pytest.mark.parametrize(
    "members",
    [
        [("../escape", tarfile.REGTYPE, "")],
        [("/workspace/absolute", tarfile.REGTYPE, "")],
        [("workspace/../escape", tarfile.REGTYPE, "")],
        [("workspace/escape", tarfile.SYMTYPE, "../../escape")],
        [("workspace/escape", tarfile.SYMTYPE, "/etc/passwd")],
        [("workspace/escape", tarfile.SYMTYPE, "../native/transcript")],
        [("workspace/hardlink", tarfile.LNKTYPE, "manifest.json")],
        [("workspace/fifo", tarfile.FIFOTYPE, "")],
        [("workspace/device", tarfile.CHRTYPE, "")],
        [("workspace/dup", tarfile.REGTYPE, ""), ("workspace/dup", tarfile.REGTYPE, "")],
        [("workspace/link", tarfile.SYMTYPE, "target"), ("workspace/link/child", tarfile.REGTYPE, "")],
        [("workspace/missing/child", tarfile.REGTYPE, "")],
        [("other/file", tarfile.REGTYPE, "")],
    ],
)
def test_unsafe_archives_never_expose_partial_restore(tmp_path, members):
    path = malicious_archive(tmp_path, members)
    with pytest.raises(SandboxError):
        CheckpointArchive().restore(path, tmp_path / "destination")
    assert not (tmp_path / "destination").exists()
    assert not list(tmp_path.glob(".restore-*"))
    assert not (tmp_path / "escape").exists()


def test_restore_never_overwrites_current_workspace(tmp_path, roots):
    source = capture(tmp_path, roots)
    with pytest.raises(FileExistsError):
        CheckpointArchive().restore(source, roots["workspace"])
    assert (roots["workspace"] / "tracked.py").read_text() == "print('hello')"


@pytest.mark.asyncio
async def test_async_capture_concurrent_upload_and_restore(tmp_path, roots):
    archive = CheckpointArchive()
    source = tmp_path / "checkpoint.tar"
    await archive.acapture(roots, source, state={"run_id": "r"})
    first, second = FileCheckpointStore(tmp_path / "objects"), FileCheckpointStore(tmp_path / "objects")
    refs = await asyncio.gather(first.aput(source), second.aput(source))
    assert refs[0] == refs[1]
    assert await second.averify(refs[0]) == first.root / refs[0].sha256
    assert await second.arestore(refs[0], tmp_path / "restored") == {"run_id": "r"}


@pytest.mark.asyncio
async def test_async_cancel_drains_write_before_returning(tmp_path, monkeypatch):
    store = FileCheckpointStore(tmp_path / "objects")
    entered, release = threading.Event(), threading.Event()
    finished = []

    def slow_put(source):
        entered.set()
        release.wait(timeout=5)
        finished.append(True)
        return CheckpointRef(hashlib.sha256(b"x").hexdigest(), 1)

    monkeypatch.setattr(store, "put", slow_put)
    task = asyncio.create_task(store.aput(Path("unused")))
    assert await asyncio.to_thread(entered.wait, 2)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished == [True]


def test_composed_symlink_escape_is_rejected(tmp_path):
    source = malicious_archive(
        tmp_path,
        [
            ("workspace/a", tarfile.SYMTYPE, "."),
            ("workspace/b", tarfile.SYMTYPE, "a/../native"),
        ],
    )
    with pytest.raises(SandboxError, match="chain escapes"):
        CheckpointArchive().restore(source, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_symlink_cycle_is_rejected(tmp_path):
    source = malicious_archive(tmp_path, [("workspace/a", tarfile.SYMTYPE, "b"), ("workspace/b", tarfile.SYMTYPE, "a")])
    with pytest.raises(SandboxError, match="cycle"):
        CheckpointArchive().restore(source, tmp_path / "restored")


def test_oversized_pax_headers_are_rejected_before_parsing(tmp_path):
    source = tmp_path / "large-pax.tar"
    with tarfile.open(source, "w", format=tarfile.PAX_FORMAT) as archive:
        info = tarfile.TarInfo("workspace/file")
        info.pax_headers = {"comment": "x" * 2000}
        archive.addfile(info)
    with pytest.raises(SandboxError, match="extension metadata"):
        CheckpointArchive(CheckpointLimits(max_manifest_bytes=1000)).restore(source, tmp_path / "restored")
