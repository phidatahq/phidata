"""Repository configuration and real local Git preparation without model calls."""

import asyncio
import base64
import json
import subprocess
import tarfile
import threading

import pytest

from agno.sandbox import Repository, repository
from agno.sandbox.checkpoint import CheckpointArchive
from agno.sandbox.transfer import DEFAULT_NATIVE_EXCLUSIONS

SPEC = {"url": "https://github.com/example/application", "branch": "main"}


@pytest.fixture
def local_repository(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    real_run = subprocess.run

    def git(*args, cwd=source):
        return real_run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()

    git("init", "--initial-branch=main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (source / "app.py").write_text("version = 1\n")
    git("add", ".")
    git("commit", "-m", "initial")
    sha = git("rev-parse", "HEAD")
    calls = []

    def local_run(args, **kwargs):
        calls.append((list(args), dict(kwargs)))
        if "fetch" in args or "ls-remote" in args:
            args = [str(source) if value == "origin" else value for value in args]
        return real_run(args, **kwargs)

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(repository.subprocess, "run", local_run)
    return source, sha, calls, git


def test_prepare_resume_and_replacement_keep_commits_and_edits(tmp_path, local_repository):
    source, sha, calls, git = local_repository
    workspace, native = tmp_path / "workspace", tmp_path / "runtime/native"
    target = repository._prepare(SPEC, workspace, native, resume=False)
    pin = {**SPEC, "commit": sha}
    assert json.loads((native / "repository.json").read_text()) == pin
    assert git("rev-parse", "HEAD", cwd=target) == sha
    assert git("rev-parse", "--is-shallow-repository", cwd=target) == "true"
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=target) == "HEAD"
    # The remote can advance after this session has been pinned.
    (source / "app.py").write_text("version = 2\n")
    git("commit", "-am", "remote advance")
    git("config", "user.email", "test@example.com", cwd=target)
    git("config", "user.name", "Test", cwd=target)
    (target / "app.py").write_text("version = 3\n")
    git("commit", "-am", "engineer", cwd=target)
    engineer_head = git("rev-parse", "HEAD", cwd=target)
    (target / "app.py").write_text("version = 4\n")
    (target / "untracked").write_text("keep me")
    count = len(calls)
    repository._prepare(SPEC, workspace, native, resume=True)
    assert len(calls) == count
    archive = CheckpointArchive()
    checkpoint = tmp_path / "checkpoint.tar"
    archive.capture({"workspace": workspace, "native": native}, checkpoint, state={}, exclude=DEFAULT_NATIVE_EXCLUSIONS)
    restored = tmp_path / "replacement"
    archive.restore(checkpoint, restored)
    checkout = repository._prepare(SPEC, restored / "workspace", restored / "native", resume=True)
    assert len(calls) == count
    assert git("rev-parse", "HEAD", cwd=checkout) == engineer_head
    assert (checkout / "app.py").read_text() == "version = 4\n"
    assert (checkout / "untracked").read_text() == "keep me"
    assert repository._read_pin(restored / "native", SPEC) == pin
    for changed in ({**SPEC, "branch": "other"}, {**SPEC, "url": "https://github.com/other/repo"}):
        with pytest.raises(ValueError, match="pinned source"):
            repository._prepare(changed, workspace, native, resume=True)
    (native / "repository.json").unlink()
    with pytest.raises(ValueError, match="source identity"):
        repository._prepare(SPEC, workspace, native, resume=True)


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/repo",
        "https://token@github.com/a/b",
        "https://evil.test/a/b",
        "https://github.com/../b",
        "https://github.com/a/b?token=secret",
        "https://github.com/a/b#main",
        "https://github.com:443/a/b",
    ],
)
def test_invalid_url(url):
    with pytest.raises(ValueError, match="repository.url"):
        Repository(url)


@pytest.mark.parametrize(
    "branch",
    [
        "",
        "-main",
        "HEAD",
        "a..b",
        "a.lock",
        "a.lock/b",
        ".a",
        "a/.b",
        "a/",
        "/a",
        "a//b",
        "a.",
        "a@{b",
        "a b",
        "a~b",
        "a^b",
        "a:b",
        "a?b",
        "a*b",
        "a[b",
        "a\\b",
        "a\n",
        "a\x7fb",
        "main",
        "feature/nested",
        "@",
        "a@b",
        "release-v1",
        "refs/heads/main",
        "café",
    ],
)
def test_branch_rules_match_git(branch):
    valid = subprocess.run(["git", "check-ref-format", "--branch", branch], capture_output=True).returncode == 0
    if valid:
        assert Repository(SPEC["url"], branch).branch == branch
    else:
        with pytest.raises(ValueError, match="repository.branch"):
            Repository(SPEC["url"], branch)


def test_config_validation_has_no_subprocess(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("configuration invoked Git"))
    assert Repository(SPEC["url"]).branch == "main"
    for value in ({**SPEC, "token": "secret"}, {"url": SPEC["url"], "commit": "a" * 40}):
        with pytest.raises(ValueError):
            repository.validate_repository(value)


@pytest.mark.parametrize("sdk", ["claude", "codex"])
def test_agent_configuration_and_run_rejection(sdk, monkeypatch):
    from agno.agents.claude import ClaudeAgent
    from agno.agents.codex import CodexAgent
    from agno.sandbox._harness import _execution, env, submission
    from agno.sandbox.docker import DockerSandbox

    cls = ClaudeAgent if sdk == "claude" else CodexAgent
    configured = Repository(**SPEC)
    with pytest.raises(ValueError, match="repository requires sandbox"):
        cls(repository=configured)
    with pytest.raises(TypeError, match="Repository"):
        cls(repository=SPEC)
    agent = cls(sandbox=DockerSandbox(image="fixture"), repository=configured)
    assert _execution(agent, "inspect", {})["config"]["repository"] == SPEC
    assert submission(agent, "inspect", {}) == {}
    monkeypatch.setenv("GITHUB_READ_TOKEN", "host-only-secret")
    assert "GITHUB_READ_TOKEN" not in env(agent)
    for method in (agent.run, agent.arun):
        for stream in (False, True):
            with pytest.raises(ValueError, match="agent.repository"):
                method("inspect", repository=None, stream=stream)
    with pytest.raises(ValueError, match="agent.repository"):
        submission(agent, "inspect", {"repository": SPEC})
    with pytest.raises(ValueError, match="GITHUB_READ_TOKEN"):
        cls(sandbox=DockerSandbox(image="fixture", env={"GITHUB_TOKEN": "publishing-secret"}))


def test_token_only_in_child_environment(tmp_path, monkeypatch, local_repository):
    _, _, calls, _ = local_repository
    token = "read-secret-never-store"
    encoded = base64.b64encode(("x-access-token:" + token).encode()).decode()
    monkeypatch.setenv("GITHUB_READ_TOKEN", token)
    monkeypatch.setenv("GIT_TRACE", str(tmp_path / "workspace/trace"))
    workspace, native = tmp_path / "workspace", tmp_path / "runtime/native"
    repository._prepare(SPEC, workspace, native, resume=False)
    for args, kwargs in calls:
        assert token not in str(args) and encoded not in str(args)
        env = kwargs["env"]
        assert "GITHUB_READ_TOKEN" not in env and "GIT_TRACE" not in env
        assert env["GIT_CONFIG_NOSYSTEM"] == "1" and env["GIT_CONFIG_GLOBAL"] == "/dev/null"
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert kwargs["timeout"] == 120
        settings = {
            env[f"GIT_CONFIG_KEY_{i}"]: env[f"GIT_CONFIG_VALUE_{i}"] for i in range(int(env["GIT_CONFIG_COUNT"]))
        }
        assert settings["http.followRedirects"] == "false"
        assert settings["http.https://github.com/.extraheader"] == "Authorization: Basic " + encoded
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert token.encode() not in path.read_bytes() and encoded.encode() not in path.read_bytes()
    archive = tmp_path / "checkpoint.tar"
    CheckpointArchive(compress=False).capture(
        {"workspace": workspace, "native": native}, archive, state={}, exclude=DEFAULT_NATIVE_EXCLUSIONS
    )
    assert token.encode() not in archive.read_bytes() and encoded.encode() not in archive.read_bytes()
    with tarfile.open(archive) as contents:
        assert "native/repository.json" in contents.getnames()


@pytest.mark.parametrize("failure", ["exit", "timeout", "oserror", "marker"])
def test_failed_preparation_redacts_and_cleans(tmp_path, monkeypatch, local_repository, failure):
    _, _, _, _ = local_repository
    secret = "credential-must-not-escape"
    monkeypatch.setenv("GITHUB_READ_TOKEN", secret)
    local_run = repository.subprocess.run

    def failed(args, **kwargs):
        if "fetch" in args:
            if failure == "exit":
                return subprocess.CompletedProcess(args, 1, secret, secret)
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args, 120, output=secret, stderr=secret)
            if failure == "oserror":
                raise OSError(secret)
        return local_run(args, **kwargs)

    monkeypatch.setattr(repository.subprocess, "run", failed)
    workspace, native = tmp_path / "workspace", tmp_path / "runtime/native"
    if failure == "marker":
        native.parent.mkdir()
        native.write_text("not a directory")
    with pytest.raises(repository.RepositoryPreparationError) as caught:
        repository._prepare(SPEC, workspace, native, resume=False)
    assert secret not in str(caught.value)
    assert not (workspace / "repository").exists()
    assert not (workspace / ".repository-prepare").exists()


@pytest.mark.asyncio
async def test_cancellation_drains_preparation(tmp_path, monkeypatch, local_repository):
    started, release = threading.Event(), threading.Event()
    original = repository._prepare

    def delayed(*args, **kwargs):
        started.set()
        release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(repository, "_prepare", delayed)
    task = asyncio.create_task(repository._aprepare(SPEC, tmp_path / "workspace", tmp_path / "native", resume=False))
    await asyncio.to_thread(started.wait, 5)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not (tmp_path / "workspace/.repository-prepare").exists()


@pytest.mark.asyncio
async def test_runtime_guards_before_model(tmp_path, monkeypatch):
    from agno.sandbox import runtime

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    native = tmp_path / "native"
    native.mkdir()
    (native / "repository.json").write_text(json.dumps({**SPEC, "commit": "a" * 40}))
    directory = tmp_path / "jobs/run"
    directory.mkdir(parents=True)
    monkeypatch.setattr(runtime, "_execute_harness", lambda *a: pytest.fail("model started"))
    with pytest.raises(ValueError, match="agent.repository"):
        await runtime._execute(directory, {"sdk": "fixture", "config": {}})
    with pytest.raises(ValueError, match="pinned source"):
        await runtime._execute(directory, {"sdk": "fixture", "config": {"repository": {**SPEC, "branch": "other"}}})


@pytest.mark.parametrize("sdk", ["claude", "codex"])
def test_runtime_sets_repository_cwd(tmp_path, sdk):
    from agno.sandbox import runtime

    agent = runtime._agent({"agent_id": "agent", "sdk": sdk, "config": {"repository": SPEC}}, tmp_path)
    try:
        assert str(agent.cwd) == "/workspace/repository"
        assert agent.repository is None
    finally:
        agent.db.db_engine.dispose()


def test_worker_preparation_failure_is_retryable_before_model(tmp_path, monkeypatch):
    from agno.sandbox import runtime

    monkeypatch.setenv("AGNO_SANDBOX_TEST_RUNTIME", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    directory = tmp_path / "jobs/first"
    directory.mkdir(parents=True)
    request = {
        "version": 1,
        "execution_id": "first",
        "sdk": "fixture",
        "input": "inspect",
        "agent_id": "a",
        "session_id": "s",
        "run_id": "r",
        "config": {"repository": SPEC},
    }
    (directory / "request.json").write_text(json.dumps(request))

    async def fail(*args, **kwargs):
        raise repository.RepositoryPreparationError("Repository preparation failed")

    monkeypatch.setattr(repository, "_aprepare", fail)
    monkeypatch.setattr(runtime, "_execute_harness", lambda *args: pytest.fail("model started"))
    runtime._worker(directory)
    result = json.loads((directory / "result.json").read_text())
    assert result["type"] == "execution_error"
    assert result["reason"] == "repository_preparation_failed"


def test_runtime_fingerprint_includes_repository(tmp_path, monkeypatch):
    from agno.sandbox import SandboxError, runtime

    monkeypatch.setenv("AGNO_SANDBOX_TEST_RUNTIME", "1")
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *a, **kw: None)
    monkeypatch.setattr(runtime, "_process_start", lambda pid: "test-start")
    request = {
        "version": 1,
        "execution_id": "first",
        "sdk": "fixture",
        "input": "inspect",
        "agent_id": "a",
        "session_id": "s",
        "run_id": "r",
        "config": {"repository": SPEC},
    }
    runtime._start(tmp_path, request)
    request["config"]["repository"] = {**SPEC, "branch": "other"}
    with pytest.raises(SandboxError, match="different input"):
        runtime._start(tmp_path, request)
