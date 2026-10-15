"""Real Git checkout and checkpoint reuse without network or model calls."""

import json
import subprocess

import pytest

from agno.sandbox import repository


def test_checkout_pins_commit_and_resume_preserves_work(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    real_run = subprocess.run

    def git(*args):
        return real_run(["git", *args], cwd=source, check=True, capture_output=True, text=True).stdout.strip()

    git("init")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (source / "app.py").write_text("version = 1\n")
    git("add", ".")
    git("commit", "-m", "initial")
    sha = git("rev-parse", "HEAD")
    (source / "app.py").write_text("version = 2\n")
    git("commit", "-am", "later")
    calls = []

    def local_run(args, **kwargs):
        calls.append(args)
        if "fetch" in args:
            args = [str(source) if value == "origin" else value for value in args]
        return real_run(args, **kwargs)

    monkeypatch.setattr(repository.subprocess, "run", local_run)
    workspace, native = tmp_path / "workspace", tmp_path / "native"
    spec = {"url": "https://github.com/example/application", "commit": sha}
    target = repository._prepare(spec, workspace, native, resume=False)
    assert (target / "app.py").read_text() == "version = 1\n"
    assert json.loads((native / "repository.json").read_text()) == spec
    (target / "app.py").write_text("version = 3\n")
    count = len(calls)
    assert repository._prepare(spec, workspace, native, resume=True) == target
    assert (target / "app.py").read_text() == "version = 3\n" and len(calls) == count
    with pytest.raises(ValueError, match="pinned source"):
        repository._prepare({**spec, "commit": "b" * 40}, workspace, native, resume=True)
    (native / "repository.json").unlink()
    with pytest.raises(ValueError, match="source identity"):
        repository._prepare(spec, workspace, native, resume=True)


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/repo",
        "https://token@github.com/a/b",
        "https://evil.test/a/b",
        "https://github.com/../b",
        "https://github.com/a/b?token=secret",
    ],
)
def test_repository_rejects_untrusted_locations(url):
    with pytest.raises(ValueError):
        repository.validate_repository({"url": url, "commit": "a" * 40})


def test_repository_requires_full_commit_and_no_extra_keys():
    for value in (
        {"url": "https://github.com/a/b", "commit": "main"},
        {"url": "https://github.com/a/b", "commit": "a" * 40, "token": "secret"},
    ):
        with pytest.raises(ValueError):
            repository.validate_repository(value)


def test_harness_passes_source_to_runtime_before_model():
    from agno.agents.codex import CodexAgent
    from agno.sandbox._harness import _execution
    from agno.sandbox.docker import DockerSandbox

    agent = CodexAgent(id="product-engineer", sandbox=DockerSandbox(image="fixture"))
    spec = {"url": "https://github.com/example/application", "commit": "a" * 40}
    request = _execution(agent, "Upgrade this application", {"repository": spec})
    assert request["config"]["_repository"] == spec
    assert "repository" not in agent.__dict__


@pytest.mark.asyncio
async def test_missing_source_cannot_bypass_resume_preparation(tmp_path, monkeypatch):
    from agno.sandbox import runtime

    native = tmp_path / "native"
    native.mkdir()
    (native / "repository.json").write_text("{}")
    directory = tmp_path / "jobs" / "run"
    directory.mkdir(parents=True)
    with pytest.raises(ValueError, match="pinned repository"):
        await runtime._execute(directory, {"sdk": "fixture", "input": "skip preparation"})
