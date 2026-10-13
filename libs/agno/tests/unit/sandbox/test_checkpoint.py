import asyncio
import errno
import gzip
import hashlib
import io
import json
import os
import tarfile
import threading
import traceback
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


def test_a_hardlink_cannot_carry_out_an_excluded_credential(tmp_path, roots):
    os.link(roots["native"] / "auth.json", roots["native"] / "session-cache")
    with pytest.raises(SandboxError, match="hardlink to excluded"):
        capture(tmp_path, roots)
    assert not (tmp_path / "checkpoint.tar").exists()


def test_an_exclusion_that_leaves_its_root_excludes_nothing_inside_it(tmp_path, roots):
    outside = tmp_path / "outside"
    outside.mkdir()
    bait = outside / "bait"
    bait.write_text("bait")
    os.link(bait, outside / "bait-alias")
    os.link(bait, roots["workspace"] / "innocent")
    (roots["native"] / "cache").symlink_to(outside)
    # Excluding the link itself stops capture rejecting it, so the exclusion scan alone
    # decides the outcome: it must not follow the link out of the root and treat what it
    # finds there as excluded content.
    archive = tmp_path / "checkpoint.tar"
    CheckpointArchive().capture(roots, archive, state={}, exclude=["native/cache", "native/cache/bait"])
    with tarfile.open(archive) as opened:
        assert "workspace/innocent" in opened.getnames()


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


def malicious_archive(tmp_path, members, manifest=None):
    path = tmp_path / "malicious.tar"
    with tarfile.open(path, "w") as archive:
        if manifest is None:
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


def test_restore_does_not_depend_on_how_the_destination_is_spelled(tmp_path, roots):
    source = capture(tmp_path, roots)
    real = tmp_path / "store"
    real.mkdir()
    (tmp_path / "store-alias").symlink_to(real)
    (tmp_path / "root-alias").symlink_to(tmp_path)
    store = FileCheckpointStore(tmp_path / "objects")
    reference = store.put(source)

    parents = (real, tmp_path / "store-alias", tmp_path / "root-alias" / "store")
    for index, parent in enumerate(parents):
        destination = parent / f"restored{index}"
        assert store.restore(reference, destination) == {"run_id": "r", "native_id": "n", "conversation": ["hello"]}
        assert (destination / "workspace/tracked.py").read_text() == "print('hello')"
        assert os.readlink(destination / "workspace/link") == "tracked.py"
        assert (destination / "workspace/link").read_text() == "print('hello')"
        assert (destination / "workspace/untracked").read_bytes() == bytes(range(256))

    # An alias must not buy a symlink its way out of the root either.
    escape = malicious_archive(tmp_path, [("workspace/escape", tarfile.SYMTYPE, "../native/transcript")])
    with pytest.raises(SandboxError, match="escapes"):
        CheckpointArchive().restore(escape, tmp_path / "store-alias" / "rejected")
    assert not (real / "rejected").exists()
    assert not list(real.glob(".restore-*"))


@pytest.mark.parametrize("links", [(("a", "a"),), (("a", "b"), ("b", "a"))])
def test_capture_rejects_cyclic_symlinks(tmp_path, roots, links):
    for name, target in links:
        (roots["workspace"] / name).symlink_to(target)
    with pytest.raises(SandboxError, match="cycle"):
        capture(tmp_path, roots)
    assert not (tmp_path / "checkpoint.tar").exists()


def test_dangling_links_survive_capture_and_restore(tmp_path, roots):
    (roots["workspace"] / "dangling").symlink_to("never-written.txt")
    source = capture(tmp_path, roots)
    destination = tmp_path / "restored"
    CheckpointArchive().restore(source, destination)
    assert os.readlink(destination / "workspace/dangling") == "never-written.txt"
    assert not (destination / "workspace/dangling").exists()


def test_archive_cut_after_the_roots_is_rejected(tmp_path, roots):
    """Cut the stream immediately after the ``workspace`` directory header: both roots
    are still declared, every workspace file is gone, and the stored digest matches
    those bytes, so nothing but the archive framing can reject it."""
    source = capture(tmp_path, roots)
    with tarfile.open(source) as archive:
        cut = next(member.offset_data for member in archive if member.name == "workspace")
    truncated = tmp_path / "truncated.tar"
    truncated.write_bytes(source.read_bytes()[:cut])
    store = FileCheckpointStore(tmp_path / "objects")
    reference = store.put(truncated)
    assert store.verify(reference) == store.root / reference.sha256
    with pytest.raises(SandboxError):
        store.restore(reference, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
    assert not list(tmp_path.glob(".restore-*"))


def unparsable_archive(tmp_path, roots, kind):
    if kind == "manifest is not json":
        return malicious_archive(tmp_path, [], manifest=b"{not json")
    if kind == "manifest is not utf-8":
        return malicious_archive(tmp_path, [], manifest='{"state": "caf\xe9"}'.encode("latin-1"))
    path = tmp_path / "unparsable.tar"
    if kind == "no tar header":
        path.write_bytes(b"x" * 4096)
        return path
    source = capture(tmp_path, roots)
    if kind == "compressed":
        path.write_bytes(gzip.compress(source.read_bytes()))
        return path
    if kind == "stream stops inside a header":
        with tarfile.open(source) as archive:
            inside = max(member.offset for member in archive) + 100
        path.write_bytes(source.read_bytes()[:inside])
        return path
    # A long-name header that no member follows. The framing walk steps over it and
    # stops on the end-of-archive marker, so only tarfile's own reader rejects this.
    data = bytearray(source.read_bytes())
    while data[-512:] == b"\x00" * 512:
        del data[-512:]
    orphan = b"workspace/orphan.txt\n"
    header = tarfile.TarInfo("././@LongLink")
    header.type, header.size = tarfile.GNUTYPE_LONGNAME, len(orphan)
    data += header.tobuf(tarfile.GNU_FORMAT, "utf-8", "surrogateescape")
    data += orphan.ljust(512, b"\x00") + b"\x00" * 1024
    path.write_bytes(bytes(data))
    return path


@pytest.mark.parametrize(
    "kind",
    [
        "no tar header",
        "compressed",
        "stream stops inside a header",
        "long-name header with no member",
        "manifest is not json",
        "manifest is not utf-8",
    ],
)
def test_unparsable_archives_are_rejected_as_sandbox_errors(tmp_path, roots, kind):
    with pytest.raises(SandboxError):
        CheckpointArchive().restore(unparsable_archive(tmp_path, roots, kind), tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
    assert not list(tmp_path.glob(".restore-*"))


def hold_upload(monkeypatch, *, fail=False):
    """Hold a real upload at its fsync boundary; ``settled`` fires when the worker leaves."""
    entered, release, settled = threading.Event(), threading.Event(), threading.Event()
    real = os.fsync

    def gate(descriptor):
        if entered.is_set():
            return real(descriptor)
        entered.set()
        assert release.wait(10), "the upload gate was never released"
        try:
            if fail:
                raise OSError(errno.ENOSPC, "injected upload failure")
            return real(descriptor)
        finally:
            settled.set()

    monkeypatch.setattr(os, "fsync", gate)
    return entered, release, settled


async def deliver(task, cancels):
    for _ in range(cancels):
        task.cancel()
        await asyncio.sleep(0)
    for _ in range(5):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_upload_failure_without_cancellation_still_reaches_the_caller(tmp_path, roots, monkeypatch):
    store = FileCheckpointStore(tmp_path / "objects")
    _, release, settled = hold_upload(monkeypatch, fail=True)
    release.set()
    with pytest.raises(OSError) as error:
        await store.aput(capture(tmp_path, roots))
    assert error.value.errno == errno.ENOSPC
    assert settled.is_set()
    assert not list(store.root.glob(".upload-*"))


@pytest.mark.asyncio
async def test_cancelled_upload_reports_cancellation_when_the_write_fails(tmp_path, roots, monkeypatch):
    store = FileCheckpointStore(tmp_path / "objects")
    entered, release, settled = hold_upload(monkeypatch, fail=True)
    task = asyncio.create_task(store.aput(capture(tmp_path, roots)))
    assert await asyncio.to_thread(entered.wait, 10)
    await deliver(task, 1)
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert settled.is_set(), "the write must settle before the caller returns"
    assert not list(store.root.glob(".upload-*"))
    assert not list(store.root.iterdir()), "a failed upload publishes nothing"


@pytest.mark.asyncio
async def test_repeated_cancellation_does_not_abandon_the_upload(tmp_path, roots, monkeypatch):
    store = FileCheckpointStore(tmp_path / "objects")
    entered, release, settled = hold_upload(monkeypatch)
    task = asyncio.create_task(store.aput(capture(tmp_path, roots)))
    assert await asyncio.to_thread(entered.wait, 10)
    await deliver(task, 3)
    assert not settled.is_set(), "the gate is still held, so the worker cannot have finished"
    assert not task.done(), "further cancellation must not detach the protected write"
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert settled.is_set()
    assert not list(store.root.glob(".upload-*"))
    assert len(list(store.root.iterdir())) == 1


@pytest.mark.asyncio
async def test_retry_immediately_after_a_cancelled_upload(tmp_path, roots, monkeypatch):
    source = capture(tmp_path, roots)
    store = FileCheckpointStore(tmp_path / "objects")
    entered, release, _ = hold_upload(monkeypatch)
    task = asyncio.create_task(store.aput(source))
    assert await asyncio.to_thread(entered.wait, 10)
    await deliver(task, 2)
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    reference = await store.aput(source)
    assert not list(store.root.glob(".upload-*"))
    assert [path.name for path in store.root.iterdir()] == [reference.sha256]
    assert await store.arestore(reference, tmp_path / "recovered") == {
        "run_id": "r",
        "native_id": "n",
        "conversation": ["hello"],
    }


@pytest.mark.asyncio
async def test_repeated_cancellation_does_not_abandon_a_capture(tmp_path, roots, monkeypatch):
    destination = tmp_path / "cancelled.tar"
    entered, release, settled = threading.Event(), threading.Event(), threading.Event()
    original = tarfile.TarFile.addfile

    def gate(archive, info, fileobj=None):
        if info.name == "workspace/tracked.py" and not entered.is_set():
            entered.set()
            assert release.wait(10), "the capture gate was never released"
            try:
                return original(archive, info, fileobj)
            finally:
                settled.set()
        return original(archive, info, fileobj)

    monkeypatch.setattr(tarfile.TarFile, "addfile", gate)
    task = asyncio.create_task(CheckpointArchive().acapture(roots, destination, state={"run_id": "r"}))
    assert await asyncio.to_thread(entered.wait, 10)
    await deliver(task, 3)
    assert not settled.is_set()
    assert not task.done(), "further cancellation must not detach a half-written archive"
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert settled.is_set()
    monkeypatch.undo()
    # The destination is settled either way: removed, or complete enough to restore.
    if destination.exists():
        assert CheckpointArchive().restore(destination, tmp_path / "from-cancelled") == {"run_id": "r"}


@pytest.mark.asyncio
async def test_draining_an_already_cancelled_operation_terminates():
    # Loop shutdown cancels the protected task itself. Draining one that is already
    # cancelled must simply return, so it neither spins nor replaces the caller's
    # cancellation with a second one.
    from agno.sandbox.checkpoint import _drain

    protected = asyncio.create_task(asyncio.sleep(3600))
    protected.cancel()
    await asyncio.wait({protected})
    assert protected.cancelled()
    await asyncio.wait_for(_drain(protected), 5)


def chained(error):
    """Every exception reachable from ``error`` by standard chaining.

    Cancellation reaches the caller through a task boundary, and how deep the drained
    failure sits differs by version: directly on ``__cause__`` from 3.11, one level
    further through ``__context__`` before it. Walk the chain instead of naming one.
    """
    seen, found = set(), []
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        found.append(error)
        error = error.__cause__ or error.__context__
    return found


@pytest.mark.asyncio
async def test_cancelled_upload_keeps_the_write_failure_reachable(tmp_path, roots, monkeypatch):
    store = FileCheckpointStore(tmp_path / "objects")
    entered, release, settled = hold_upload(monkeypatch, fail=True)
    task = asyncio.create_task(store.aput(capture(tmp_path, roots)))
    try:
        assert await asyncio.to_thread(entered.wait, 10)
        await deliver(task, 1)
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError) as error:
        await task
    assert settled.is_set(), "the write must settle before the caller returns"

    failures = [item for item in chained(error.value) if isinstance(item, OSError)]
    assert failures, "the write failure must stay reachable from the cancellation"
    assert failures[0].errno == errno.ENOSPC
    assert "injected upload failure" in str(failures[0])
    # The failure keeps the frames where the write actually died, not a re-raise site.
    assert "os.fsync(output.fileno())" in "".join(traceback.format_tb(failures[0].__traceback__))
    rendered = "".join(traceback.format_exception(type(error.value), error.value, error.value.__traceback__))
    assert "injected upload failure" in rendered, "chained formatting must show the write failure"
    assert "CancelledError" in rendered

    assert not list(store.root.glob(".upload-*"))
    assert not list(store.root.iterdir()), "a failed upload publishes nothing"


@pytest.mark.asyncio
async def test_repeated_cancellation_keeps_the_write_failure_reachable(tmp_path, roots, monkeypatch):
    store = FileCheckpointStore(tmp_path / "objects")
    entered, release, settled = hold_upload(monkeypatch, fail=True)
    task = asyncio.create_task(store.aput(capture(tmp_path, roots)))
    try:
        assert await asyncio.to_thread(entered.wait, 10)
        await deliver(task, 3)
        assert not settled.is_set(), "the gate is still held, so the worker cannot have finished"
        assert not task.done(), "further cancellation must not detach the protected write"
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError) as error:
        await task
    assert settled.is_set()

    failures = [item for item in chained(error.value) if isinstance(item, OSError)]
    assert failures, "repeated cancellation must not erase the write failure"
    assert failures[0].errno == errno.ENOSPC
    assert "injected upload failure" in "".join(
        traceback.format_exception(type(error.value), error.value, error.value.__traceback__)
    )
    assert not list(store.root.glob(".upload-*"))
    assert not list(store.root.iterdir())
