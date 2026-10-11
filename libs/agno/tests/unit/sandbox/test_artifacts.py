from types import SimpleNamespace

import pytest

from agno.sandbox.artifacts import SandboxArtifactNotFound, SandboxArtifacts
from agno.sandbox.checkpoint import CheckpointArchive, FileCheckpointStore


@pytest.fixture
def artifact_store(tmp_path):
    workspace, native = tmp_path / "workspace", tmp_path / "native"
    workspace.mkdir()
    native.mkdir()
    (workspace / "a.txt").write_bytes(b"a")
    (workspace / "b.txt").write_bytes(b"binary\x00data")
    (workspace / "alias").symlink_to("a.txt")
    (native / "session.db").write_bytes(b"native state")
    identity = {"incarnation": "inc", "agent_id": "agent", "session_id": "session", "run_id": "run"}
    archive = tmp_path / "archive"
    CheckpointArchive().capture({"workspace": workspace, "native": native}, archive, state={"binding": identity})
    objects = FileCheckpointStore(tmp_path / "objects")
    reference = objects.put(archive)
    record = {
        "checkpoint": {"sha256": reference.sha256, "size": reference.size},
        "checkpoint_identity": identity,
        "incarnation": "inc",
        "last_run_id": "run",
    }
    return SandboxArtifacts(SimpleNamespace(), objects), record


def test_binary_artifact_and_paginated_regular_workspace_listing(artifact_store):
    store, record = artifact_store
    first = store._inspect(record, None, 0, 1)
    second = store._inspect(record, None, 1, 1)
    assert first["total"] == second["total"] == 2
    assert first["files"] == [{"path": "a.txt", "size": 1}]
    assert second["files"] == [{"path": "b.txt", "size": 11}]
    artifact = store._inspect(record, "b.txt", 0, 1)
    assert artifact.content == b"binary\x00data" and artifact.run_id == "run"


@pytest.mark.parametrize("path", ["alias", "native/session.db", "absent"])
def test_symlinks_native_state_and_missing_files_are_not_downloadable(artifact_store, path):
    store, record = artifact_store
    with pytest.raises(SandboxArtifactNotFound):
        store._inspect(record, path, 0, 1)


def test_no_checkpoint_has_no_durable_artifact(artifact_store):
    store, record = artifact_store
    record["checkpoint"] = None
    with pytest.raises(SandboxArtifactNotFound):
        store._inspect(record, "a.txt", 0, 1)
