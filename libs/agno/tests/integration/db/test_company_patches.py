"""Checkpoint output projection on SQLite/Postgres using the local repository fixture."""

# Reused pytest fixtures are intentionally shadowed by test arguments.
# ruff: noqa: F811

import hashlib
import json
import shutil
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from agno.company.checkpoints import _checkpoint_store, open_run_checkpoint, open_run_checkpoint_sync
from agno.company.execution import _call, _project_run, _sandbox_task_input, _task_input
from agno.company.manager import AsyncCompanyManager, CompanyManager
from agno.company.patches import _filesystem, aread_task_patch, read_task_patch
from agno.db.base import AsyncBaseDb
from agno.db.postgres import PostgresDb
from agno.os.routers.company.tasks import get_tasks_router
from agno.os.settings import AgnoAPISettings
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from agno.sandbox import Repository, repository
from agno.sandbox.checkpoint import CheckpointArchive, FileCheckpointStore
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.fixture import FixtureAgent
from tests.integration.db.test_company_playbook_parity import db  # noqa: F401
from tests.unit.sandbox.test_repository import SPEC, local_repository  # noqa: F401


@pytest.fixture
def checkpoint(tmp_path, local_repository):
    _, commit, _, git = local_repository
    workspace, native = tmp_path / "workspace", tmp_path / "native"
    checkout = repository._prepare(SPEC, workspace, native, resume=False)
    store = FileCheckpointStore(tmp_path / "objects")
    agent = FixtureAgent(
        id="engineer",
        db=PostgresDb(db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
        sandbox=DockerSandbox("unused", checkpoints=store, env={"AGNO_SANDBOX_TEST_RUNTIME": "1"}),
        repository=Repository(**SPEC),
    )

    def capture():
        archive = tmp_path / "captured.tar"
        CheckpointArchive().capture({"workspace": workspace, "native": native}, archive, state={})
        return asdict(store.put(archive))

    return agent, checkout, commit, capture, git


async def prepare(db, checkpoint):
    agent, checkout, commit, capture, git = checkpoint
    manager = (AsyncCompanyManager if isinstance(db, AsyncBaseDb) else CompanyManager)(db)
    product = await _call(manager, "create", name="Code")
    project = await _call(manager, "create_project", product_id=product["id"], name="Release")
    task = await _call(
        manager,
        "create_task",
        product_id=product["id"],
        project_id=project["id"],
        title="Change",
        brief="Implement",
        evidence=[{"source": "evidence"}],
    )
    await _call(manager, "create_source", product_id=product["id"], type="git", reference=SPEC["url"])
    task = await _call(
        db, "transition_task", task["id"], "ready", "Reviewed", executor_type="agent", executor_id=agent.id
    )
    history = task["transitions"]
    task = await _call(db, "start_task_run", task["id"], 1, history)
    worker = SimpleNamespace(_company_db=db, _aresolve_job_component=AsyncMock(return_value=agent))
    job = {
        "id": task["job_id"],
        "session_id": task["session_id"],
        "component_id": agent.id,
        "component_type": "agent",
        "payload": {"company_task_id": task["id"], "company_task_attempt": 1, "company_task_transitions": history},
    }
    return manager, task, worker, job


def output(agent, task, commit, reference):
    return RunOutput(
        run_id=task["job_id"],
        agent_id=agent.id,
        session_id=task["session_id"],
        status=RunStatus.completed,
        content="Work complete",
        metadata={"sandbox": {"repository": {**SPEC, "commit": commit}, "checkpoint": reference}},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["changes", "empty", "wrong_head", "oversize"])
async def test_projection_and_download(db, checkpoint, case):
    agent, checkout, commit, capture, git = checkpoint
    manager, task, worker, job = await prepare(db, checkpoint)
    if case != "empty":
        (checkout / "app.py").write_text("version = 2\n")
        (checkout / "new file.txt").write_text("new\n")
    if case == "wrong_head":
        git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-am", "changed", cwd=checkout)
    if case == "oversize":
        worker._company_max_patch_bytes = 1
    reference = capture()
    agent.aget_run_output = AsyncMock(return_value=output(agent, task, commit, reference))
    await _project_run(worker, job, "completed")
    saved = await _call(db, "get_task", task["id"])
    result = saved["result"]
    if case in {"wrong_head", "oversize"}:
        assert saved["status"] == "in_progress" and result["status"] == "ERROR"
        assert (
            "differs from Task checkout commit" if case == "wrong_head" else "bytes, exceeding max_patch_bytes=1"
        ) in result["content"]
        assert await aread_task_patch(db, task, 1) is None
        return
    assert saved["status"] == "in_review" and result["summary"] == "Work complete"
    patch = await aread_task_patch(db, task, 1)
    assert result["patch_sha256"] == hashlib.sha256(patch.encode()).hexdigest()
    assert result["patch_path"] == f"patches/{task['id']}/1.patch"
    assert "patch" not in result
    if not isinstance(db, AsyncBaseDb):
        assert read_task_patch(db, task, 1) == patch
    if case == "empty":
        assert patch == "" and result["changed_files"] == []
    else:
        assert result["changed_files"] == [
            {"path": "app.py", "status": "M", "added": 1, "removed": 1},
            {"path": "new file.txt", "status": "A", "added": 1, "removed": 0},
        ]
        # Restoring onto a replacement computer and losing the old workspace changes no output bytes.
        restored = checkout.parent.parent / "replacement"
        with agent.sandbox.checkpoints.open_archive(SimpleNamespace(**reference)) as archive:
            CheckpointArchive().restore(archive, restored)
        shutil.rmtree(checkout.parent)
        from agno.company.patches import _extract_patch

        replacement_patch, _ = await _extract_patch(restored / "workspace/repository", commit)
        assert replacement_patch == patch
    assert all(row.path.endswith(".md") for row in (await _call(manager, "list_wiki", task["product_id"]))[0])
    app = FastAPI()
    app.include_router(get_tasks_router(db, AgnoAPISettings()))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        for query in ("", "?attempt=1"):
            response = await client.get(f"/company/tasks/{task['id']}/patch" + query)
            assert response.status_code == 200, response.text
            assert response.content == patch.encode()
            assert response.headers["content-type"].startswith("text/x-patch")
        assert (await client.get(f"/company/tasks/{task['id']}/patch?attempt=2")).status_code == 404
        response = await client.get(f"/company/tasks/{task['id']}")
        assert response.json()["result"]["patch_sha256"] == result["patch_sha256"]


@pytest.mark.asyncio
async def test_checkpoint_access_contract(checkpoint):
    agent, _, commit, capture, _ = checkpoint
    data = output(agent, {"job_id": "run", "session_id": "session"}, commit, capture()).to_dict()
    # Exercise the actual private builder: a rename must fail this compatibility test.
    assert _checkpoint_store(agent) is agent.sandbox.checkpoints
    async with open_run_checkpoint(agent, data) as path:
        assert path.is_file()
    with open_run_checkpoint_sync(agent, data) as path:
        assert path.is_file()
    for update, reason in [
        ({"agent_id": "other"}, "another agent"),
        ({"status": "RUNNING"}, "COMPLETED"),
        ({"metadata": {}}, "no committed checkpoint"),
    ]:
        with pytest.raises(ValueError, match=reason):
            async with open_run_checkpoint(agent, {**data, **update}):
                pass
        with pytest.raises(ValueError, match=reason):
            with open_run_checkpoint_sync(agent, {**data, **update}):
                pass


@pytest.mark.asyncio
async def test_attachment_limits_and_plain_message(db, checkpoint):
    manager, task, _, _ = await prepare(db, checkpoint)
    fs = _filesystem(db, task["product_id"])
    await fs.awrite("oversized.md", "z" * (512 * 1024 + 1))
    for index in range(18):
        await fs.awrite(f"pages/{index:02}.md", "é" * (index + 1))
    message, files = await _sandbox_task_input(manager, task)
    decoded = json.loads(message)
    assert len(files) == 16 and sum(len(content) for _, content in files) <= 512 * 1024
    assert [len(content) for _, content in files] == sorted(len(content) for _, content in files)
    assert "oversized.md" in decoded["note"] and "pages/17.md" in decoded["note"]
    assert decoded["brief"] == "Implement" and decoded["evidence"] == [{"source": "evidence"}]
    assert "wiki" not in decoded and len({name for name, _ in files}) == 16
    plain = json.loads(await _task_input(manager, task))
    assert set(plain) == {"brief", "wiki", "evidence"}
    assert {page["namespace"] for page in plain["wiki"]} == {"company", "product"}


@pytest.mark.asyncio
async def test_multipart_route_preserves_attachments():
    from fastapi import File, Form, UploadFile
    from starlette.requests import Request

    from agno.os.routers.company.runs import _run_route

    app = FastAPI()

    @app.post("/agents/test/runs")
    async def receiver(message: str = Form(...), files: list[UploadFile] = File(...)):
        return {
            "message": message,
            "files": [{"name": file.filename, "content": (await file.read()).decode()} for file in files],
        }

    @app.post("/company/tasks/t/runs")
    async def dispatch(request: Request):
        return await _run_route(
            request, "/agents/test/runs", "POST", {"message": "brief"}, files=[("notes.md", b"contents")]
        )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/company/tasks/t/runs")
    assert response.status_code == 200, response.text
    assert response.json() == {"message": "brief", "files": [{"name": "notes.md", "content": "contents"}]}


@pytest.mark.asyncio
async def test_byte_budget_truncates_whole_pages(db, checkpoint):
    manager, task, _, _ = await prepare(db, checkpoint)
    fs = _filesystem(db, task["product_id"])
    await fs.awrite("first.md", "é" * 130000)
    await fs.awrite("second.md", "é" * 135000)
    message, files = await _sandbox_task_input(manager, task)
    assert len(files) < 16
    assert sum(len(data) for _, data in files) <= 512 * 1024
    assert "second.md" in json.loads(message)["note"]
    assert any(data == ("é" * 130000).encode() for _, data in files)


@pytest.mark.asyncio
async def test_checkpoint_git_configuration_never_executes(checkpoint, tmp_path):
    from agno.company.patches import _extract_patch

    _, checkout, commit, _, git = checkpoint
    marker = tmp_path / "executed"
    git("config", "filter.host.clean", "touch " + str(marker), cwd=checkout)
    git("config", "core.fsmonitor", "touch " + str(marker), cwd=checkout)
    (checkout / ".gitattributes").write_text("*.txt filter=host\n")
    (checkout / "new.txt").write_text("keep https://x-access-token:exact@github.com/owner/repo\n")
    patch, changed = await _extract_patch(checkout, commit)
    assert not marker.exists()
    assert "x-access-token:exact@" in patch
    assert {row["path"] for row in changed} == {".gitattributes", "new.txt"}


@pytest.mark.asyncio
async def test_lost_projection_recovers_the_same_patch(db, checkpoint, monkeypatch):
    from agno.company.execution import _reconcile_task_run

    agent, checkout, commit, capture, _ = checkpoint
    _, task, worker, job = await prepare(db, checkpoint)
    (checkout / "recovered.txt").write_text("durable\n")
    run = output(agent, task, commit, capture())
    from agno.session import AgentSession

    await _call(db, "upsert_session", AgentSession(session_id=task["session_id"], agent_id=agent.id, created_at=1))
    await _call(db, "upsert_run", run, session_id=task["session_id"])
    agent.aget_run_output = AsyncMock(return_value=run)

    def unavailable(*args, **kwargs):
        raise RuntimeError("projection interrupted")

    with monkeypatch.context() as failure:
        failure.setattr(db, "complete_task_run", unavailable)
        with pytest.raises(RuntimeError, match="projection interrupted"):
            await _project_run(worker, job, "completed")
    patch = await aread_task_patch(db, task, 1)
    assert patch and (await _call(db, "get_task", task["id"]))["status"] == "in_progress"
    row = await _call(db, "get_run", run.run_id, deserialize=False)
    assert await _reconcile_task_run(db, db, task, row, None, worker=worker)
    saved = await _call(db, "get_task", task["id"])
    assert saved["status"] == "in_review"
    assert saved["result"]["patch_sha256"] == hashlib.sha256(patch.encode()).hexdigest()
    assert await aread_task_patch(db, task, 1) == patch


@pytest.mark.asyncio
async def test_plain_executor_has_no_patch_fields(db, checkpoint):
    from agno.agent import Agent

    _, task, worker, job = await prepare(db, checkpoint)
    agent = Agent(id="engineer", db=db)
    agent.aget_run_output = AsyncMock(
        return_value=RunOutput(run_id=task["job_id"], agent_id=agent.id, status=RunStatus.completed, content="plain")
    )
    worker._aresolve_job_component = AsyncMock(return_value=agent)
    await _project_run(worker, job, "completed")
    saved = await _call(db, "get_task", task["id"])
    assert saved["status"] == "in_review"
    assert not {"patch_path", "patch_sha256", "changed_files", "summary"}.intersection(saved["result"])
    assert await aread_task_patch(db, task, 1) is None


@pytest.mark.asyncio
async def test_binary_and_large_patch_survive_filesystem_roundtrip(db, checkpoint):
    agent, checkout, commit, capture, git = checkpoint
    _, task, worker, job = await prepare(db, checkpoint)
    binary = bytes(range(256))
    (checkout / "binary.dat").write_bytes(binary)
    (checkout / "large.txt").write_text("x" * 1_100_000 + "\n")
    agent.aget_run_output = AsyncMock(return_value=output(agent, task, commit, capture()))
    await _project_run(worker, job, "completed")
    saved = await _call(db, "get_task", task["id"])
    assert saved["status"] == "in_review", saved["result"]
    patch = await aread_task_patch(db, task, 1)
    assert 1_000_000 < len(patch.encode()) < 2 * 1024 * 1024
    assert saved["result"]["changed_files"][0] == {"path": "binary.dat", "status": "A", "added": None, "removed": None}
    (checkout / "binary.dat").unlink()
    (checkout / "large.txt").unlink()
    patch_file = checkout.parent / "apply.patch"
    patch_file.write_bytes(patch.encode())
    git("apply", str(patch_file), cwd=checkout)
    assert (checkout / "binary.dat").read_bytes() == binary
    assert (checkout / "large.txt").stat().st_size == 1_100_001
