"""Attachment staging failures must not leak files or trust historical write paths."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from agno.agents import _media


def attachment(name, data=b"payload"):
    return SimpleNamespace(filename=name, content=data)


def fail_open(monkeypatch, name="second.txt"):
    original = Path.open

    def opening(path, *args, **kwargs):
        if path.name == name and args and args[0] == "xb":
            raise OSError("injected staging failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", opening)


def test_staging_rolls_back_only_its_new_files(tmp_path, monkeypatch):
    root = _media.uploads_root(tmp_path, "run")
    root.mkdir(parents=True)
    (root / "first.txt").write_bytes(b"user edit")
    fail_open(monkeypatch)
    with pytest.raises(OSError, match="injected"):
        _media.stage_media(tmp_path, "run", {"files": [attachment("first.txt"), attachment("second.txt")]})
    assert list(root.iterdir()) == [root / "first.txt"]
    assert (root / "first.txt").read_bytes() == b"user edit"


def test_partial_write_is_removed(tmp_path, monkeypatch):
    original = Path.open

    class FailingWrite:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def write(self, data):
            self.file.write(data[:1])
            raise OSError("disk full")

        def __exit__(self, *args):
            self.file.close()

    def opening(path, *args, **kwargs):
        file = original(path, *args, **kwargs)
        return FailingWrite(file) if args and args[0] == "xb" else file

    monkeypatch.setattr(Path, "open", opening)
    with pytest.raises(OSError, match="disk full"):
        _media.stage_media(tmp_path, "run", {"files": [attachment("first.txt")]})
    assert not (tmp_path / ".agno").exists()


@pytest.mark.parametrize("run_id", ["../escape", "/outside", "..", ".", "", "a/b", "a\\b", "C:escape"])
def test_run_ids_cannot_escape_the_upload_directory(tmp_path, run_id):
    with pytest.raises(ValueError, match="run_id"):
        _media.stage_media(tmp_path, run_id, {"files": [attachment("x")]})
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("level", [".agno", ".agno/uploads", ".agno/uploads/run"])
def test_directory_symlinks_are_rejected(tmp_path, level):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    outside.mkdir()
    link = workspace / level
    link.parent.mkdir(parents=True)
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        _media.stage_media(workspace, "run", {"files": [attachment("x")]})
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("reuse", [False, True])
def test_leaf_symlinks_are_not_followed_or_reused(tmp_path, reuse):
    outside = tmp_path / "secret"
    outside.write_bytes(b"private")
    root = _media.uploads_root(tmp_path, "run")
    root.mkdir(parents=True)
    (root / "x").symlink_to(outside)
    with pytest.raises(ValueError, match="symlinks"):
        _media.stage_media(tmp_path, "run", {"files": [attachment("x")]}, reuse_existing=reuse)
    assert outside.read_bytes() == b"private"


def test_writable_historical_root_is_only_a_locator(tmp_path, monkeypatch):
    outside = tmp_path / "previous-replica"
    outside.mkdir()
    session = SimpleNamespace(session_data={"uploads_root": str(outside)})
    monkeypatch.setattr(_media, "prior_attachments", lambda *a: {"old": {"files": [attachment("x")]}})
    workspace = tmp_path / "current"
    folders, note = _media.stage_prior_media(workspace, session)
    assert list(outside.iterdir()) == []
    assert (workspace / ".agno/uploads/old/x").read_bytes() == b"payload"
    assert folders == [workspace / ".agno/uploads/old"]
    assert "have moved" in note


def test_restore_failure_rolls_back_new_files_across_runs(tmp_path, monkeypatch):
    existing = _media.uploads_root(tmp_path, "first")
    existing.mkdir(parents=True)
    (existing / "retained.txt").write_bytes(b"keep")
    monkeypatch.setattr(
        _media,
        "prior_attachments",
        lambda *a: {
            "first": {"files": [attachment("first.txt")]},
            "second": {"files": [attachment("second.txt")]},
        },
    )
    fail_open(monkeypatch)
    with pytest.raises(OSError, match="injected"):
        _media.stage_prior_media(tmp_path, None)
    assert list(existing.iterdir()) == [existing / "retained.txt"]


@pytest.mark.asyncio
@pytest.mark.parametrize("harness", ["claude", "codex", "codex_stream"])
@pytest.mark.parametrize("keep", [False, True])
async def test_prior_restore_failure_cleans_current_input_before_sdk(tmp_path, monkeypatch, harness, keep):
    if harness == "claude":
        from agno.agents.claude import ClaudeAgent
        from agno.agents.claude import agent as module

        agent = ClaudeAgent(id="test", cwd=tmp_path, keep_uploads=keep)
    else:
        from agno.agents.codex import CodexAgent
        from agno.agents.codex import agent as module

        agent = CodexAgent(id="test", cwd=str(tmp_path), keep_uploads=keep)

    def fail(*args, **kwargs):
        raise OSError("prior restore failed")

    monkeypatch.setattr(module, "stage_prior_media", fail)
    kwargs = dict(run_id="current", media={"files": [attachment("current.txt")]})
    with pytest.raises(OSError, match="prior restore failed"):
        if harness == "claude":
            async for _ in agent._aquery("input", None, streaming=False, **kwargs):
                pytest.fail("SDK was reached")
        elif harness == "codex_stream":
            async for _ in agent._arun_adapter_stream("input", **kwargs):
                pytest.fail("SDK was reached")
        else:
            await agent._arun_adapter("input", **kwargs)
    assert not (tmp_path / ".agno").exists()


def test_cleanup_preserves_preexisting_inputs_and_duplicate_names(tmp_path):
    root = _media.uploads_root(tmp_path, "run")
    root.mkdir(parents=True)
    (root / "x.txt").write_bytes(b"retained")
    staged = _media.stage_media(tmp_path, "run", {"files": [attachment("x.txt"), attachment("x.txt")]})
    assert [item.name for item in staged] == ["x-2.txt", "x-2-3.txt"]
    _media.cleanup_staged_media(staged)
    assert list(root.iterdir()) == [root / "x.txt"]
    assert (root / "x.txt").read_bytes() == b"retained"
