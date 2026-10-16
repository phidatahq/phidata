"""Real Git publication and SQL persistence with recorded GitHub response shapes."""

# ruff: noqa: F811
import asyncio
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from agno.company.execution import _call
from agno.company.manager import AsyncCompanyManager, CompanyManager
from agno.company.patches import _filesystem, _patch_path
from agno.company.publish import apublish_task, areconcile_task, publish_task, reconcile_task
from agno.context.wiki import git_ops
from agno.db.base import AsyncBaseDb
from agno.os.routers.company.tasks import get_tasks_router
from agno.os.settings import AgnoAPISettings
from tests.integration.db.test_company_playbook_parity import db  # noqa: F401
from tests.unit.sandbox.test_repository import SPEC, local_repository  # noqa: F401

TOKEN = "company-write-secret-never-persist"


@pytest.fixture
def remote(local_repository, tmp_path, monkeypatch):
    source, commit, _, git = local_repository
    bare = tmp_path / "remote.git"
    git("clone", "--bare", str(source), str(bare))
    real_run = git_ops.run
    calls = []

    async def run(args, **kwargs):
        calls.append((list(args), copy.deepcopy(kwargs)))
        assert TOKEN not in json.dumps(args)
        assert kwargs["inherit_env"] is False
        if "remote" in args and "add" in args:
            # Production validation retains its GitHub-only URL contract.
            args = [str(bare) if arg == SPEC["url"] else arg for arg in args]
        elif "fetch" in args:
            args = [str(bare) if arg == SPEC["url"] else arg for arg in args]
        result = await real_run(args, **kwargs)
        config = Path(kwargs["cwd"]) / ".git/config"
        if config.exists():
            assert TOKEN not in config.read_text()
        return result

    monkeypatch.setattr(git_ops, "run", run)
    monkeypatch.setenv("COMPANY_PUBLISH_TOKEN", TOKEN)
    return SimpleNamespace(source=source, bare=bare, commit=commit, git=git, calls=calls)


@pytest.fixture
def api(monkeypatch, remote):
    from github.Requester import Requester

    records = json.loads((Path(__file__).parents[2] / "fixtures/github_publication.json").read_text())
    state = SimpleNamespace(pr=None, creates=0, updates=0, crash=False, checks=[], calls=[])

    def request(self, verb, url, parameters=None, headers=None, input=None, **kwargs):
        state.calls.append((verb, url, parameters, input))
        if url.endswith("/pulls") and verb == "GET":
            prs = [] if state.pr is None else [state.pr]
            if (parameters or {}).get("state") == "open":
                prs = [pr for pr in prs if pr["state"] == "open"]
            return {}, copy.deepcopy(prs)
        if url.endswith("/pulls") and verb == "POST":
            if state.crash:
                state.crash = False
                raise RuntimeError("simulated crash after push")
            assert state.pr is None, "duplicate PR"
            state.creates += 1
            state.pr = copy.deepcopy(records["pull_request"])
            state.pr.update(title=input["title"], body=input["body"])
            state.pr["head"]["ref"] = input["head"]
            state.pr["base"]["ref"] = input["base"]
            state.pr["head"]["sha"] = remote.git("rev-parse", "refs/heads/" + input["head"], cwd=remote.bare)
            return {}, copy.deepcopy(state.pr)
        if "/pulls/" in url:
            assert state.pr
            if verb == "PATCH":
                state.updates += 1
                for name in ("title", "body"):
                    if name in input:
                        state.pr[name] = input[name]
                if "base" in input:
                    state.pr["base"]["ref"] = input["base"]
                state.pr["head"]["sha"] = remote.git(
                    "rev-parse", "refs/heads/" + state.pr["head"]["ref"], cwd=remote.bare
                )
            return {}, copy.deepcopy(state.pr)
        if url.endswith("/check-runs"):
            sha = url.split("/commits/")[1].split("/")[0]
            runs = [{**row, "head_sha": row.get("head_sha", sha)} for row in state.checks]
            return {}, {"total_count": len(runs), "check_runs": runs}
        if "/commits/" in url:
            return {}, {"sha": url.rsplit("/", 1)[1], "url": url}
        if url.endswith("/repos/example/application"):
            return {}, copy.deepcopy(records["repository"])
        raise AssertionError((verb, url, parameters, input))

    monkeypatch.setattr(Requester, "requestJsonAndCheck", request)
    return state


async def prepare(db, remote, publish_ref="COMPANY_PUBLISH_TOKEN"):
    manager = (AsyncCompanyManager if isinstance(db, AsyncBaseDb) else CompanyManager)(db)
    product = await _call(manager, "create", name="Code")
    source = await _call(
        manager,
        "create_source",
        product_id=product["id"],
        type="git",
        reference=SPEC["url"],
        config={"branch": "main", **({"publish_credential_ref": publish_ref} if publish_ref else {})},
    )
    project = await _call(manager, "create_project", product_id=product["id"], name="Release")
    task = await _call(
        manager,
        "create_task",
        product_id=product["id"],
        project_id=project["id"],
        title="Update application",
        brief="Make the requested change",
    )
    task = await _call(
        db, "transition_task", task["id"], "ready", "Reviewed", executor_type="agent", executor_id="engineer"
    )
    checkout = {**SPEC, "commit": remote.commit, "source_id": source["id"]}
    return manager, await complete(db, remote, task, 1, checkout)


async def complete(db, remote, task, attempt, checkout=None):
    task = await _call(db, "start_task_run", task["id"], attempt, task["transitions"])
    (remote.source / "app.py").write_text("version = " + str(attempt + 1) + "\n")
    patch = remote.git("diff", "--binary", "--full-index", remote.commit) + "\n"
    await _filesystem(db, task["product_id"]).awrite(_patch_path(task["id"], attempt), patch)
    result = {
        "status": "COMPLETED",
        "run_id": task["job_id"],
        "summary": "Changed application",
        "patch_path": _patch_path(task["id"], attempt),
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "changed_files": [{"path": "app.py"}],
    }
    return await _call(
        db,
        "complete_task_run",
        task["id"],
        task["job_id"],
        result,
        expected_transitions=task["transitions"],
        checkout=checkout,
    )


@pytest.mark.asyncio
async def test_publication_retry_revision_and_secrets(db, remote, api, caplog):
    manager, task = await prepare(db, remote)
    pr = await apublish_task(db, task["id"])
    assert api.creates == 1 and pr["branch"] == "company/task-" + task["id"]
    assert pr["head_sha"] == remote.git("rev-parse", pr["branch"], cwd=remote.bare)
    message = remote.git("show", "-s", "--format=%B", pr["head_sha"], cwd=remote.bare)
    assert task["title"] in message and task["id"] in message and task["job_id"] in message and "Attempt: 1" in message
    assert "Make the requested change" in api.pr["body"] and task["id"] in api.pr["body"]
    if isinstance(db, AsyncBaseDb):
        again = await apublish_task(db, task["id"])
    else:
        again = await asyncio.to_thread(publish_task, db, task["id"])
    assert again == pr and api.creates == 1
    saved = await _call(db, "get_task", task["id"])
    saved = await _call(
        db, "update_task_publication", saved, {**saved["result"], "review_evidence": {"approved": True}}
    )
    # A same-head retry keeps evidence; a changed head invalidates it.
    await apublish_task(db, task["id"])
    assert (await _call(db, "get_task", task["id"]))["result"]["review_evidence"]
    revised = await complete(db, remote, saved, 2)
    second = await apublish_task(db, revised["id"])
    assert second["number"] == pr["number"] and second["head_sha"] != pr["head_sha"] and api.creates == 1
    saved = await _call(db, "get_task", task["id"])
    assert "review_evidence" not in saved["result"]
    assert TOKEN not in json.dumps(saved) + json.dumps(api.calls) + caplog.text
    assert remote.calls and all(call[1]["env"]["AGNO_GIT_TOKEN"] == TOKEN for call in remote.calls)
    assert all(TOKEN not in json.dumps(call[0]) for call in remote.calls)
    # Explicit old-attempt publication uses that attempt's original stored digest.
    old = await apublish_task(db, task["id"], attempt=1)
    assert old["head_sha"] == pr["head_sha"] and api.creates == 1
    assert (await _call(manager, "get_task", task["id"]))["result"]["published_attempt"] == 1


@pytest.mark.asyncio
async def test_crash_after_push_adopts_branch(db, remote, api):
    _, task = await prepare(db, remote)
    api.crash = True
    with pytest.raises(ValueError, match="simulated crash"):
        await apublish_task(db, task["id"])
    branch = "company/task-" + task["id"]
    head = remote.git("rev-parse", branch, cwd=remote.bare)
    assert api.creates == 0
    pr = await apublish_task(db, task["id"])
    assert pr["head_sha"] == head and api.creates == 1
    assert sum("push" in args for args, _ in remote.calls) == 1
    await apublish_task(db, task["id"])
    assert api.creates == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["verified", "different", "closed", "squashed"])
async def test_reconciliation(db, remote, api, state):
    manager, task = await prepare(db, remote)
    pr = await apublish_task(db, task["id"])
    api.pr["state"] = "closed"
    if state != "closed":
        # Build a genuine merge graph; the mismatch uses an unrelated commit.
        remote.git("reset", "--hard", remote.commit)
        remote.git("fetch", str(remote.bare), pr["branch"])
        if state == "verified":
            remote.git("merge", "--no-ff", "FETCH_HEAD", "-m", "Merge task")
        else:
            (remote.source / "app.py").write_text("unrelated = True\n")
            remote.git("commit", "-am", "Different change")
        merge = remote.git("rev-parse", "HEAD")
        remote.git("push", str(remote.bare), "HEAD:main")
        api.pr.update(merged=True, merge_commit_sha=merge)
        if state == "different":
            api.pr["head"]["sha"] = merge
    if isinstance(db, AsyncBaseDb):
        saved = await areconcile_task(db, task["id"])
    else:
        saved = await asyncio.to_thread(reconcile_task, db, task["id"])
    assert saved["status"] == ("done" if state == "verified" else "in_review")
    if state == "verified":
        assert saved["result"]["merge_commit"] == merge
        assert saved["transitions"][-1]["reason"] == "Verified merge"
    else:
        assert "merge_commit" not in saved["result"]
        assert saved["result"]["pr_observation"]["state"] == "closed"
    # Refresh uses the same reconciler and does not create a second transition.
    await _call(manager, "refresh", task["product_id"])
    assert (await _call(db, "get_task", task["id"]))["transitions"] == saved["transitions"]


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["patch", "credential", "environment", "digest"])
async def test_publication_route_refuses_missing_input(db, remote, api, monkeypatch, missing):
    _, task = await prepare(db, remote, publish_ref=None if missing == "credential" else "COMPANY_PUBLISH_TOKEN")
    if missing == "environment":
        monkeypatch.delenv("COMPANY_PUBLISH_TOKEN")
    if missing == "patch":
        await _filesystem(db, task["product_id"]).adelete(_patch_path(task["id"], 1))
    if missing == "digest":
        await _filesystem(db, task["product_id"]).awrite(_patch_path(task["id"], 1), "tampered")
    app = FastAPI()
    app.include_router(get_tasks_router(db, AgnoAPISettings()))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://company") as client:
        response = await client.post("/company/tasks/" + task["id"] + "/publish")
    assert response.status_code == 409, response.text
    assert not api.creates and not remote.calls


@pytest.mark.asyncio
async def test_publication_route_success_and_scope(db, remote, api):
    from agno.os.authz.provider import AuthorizationContext
    from agno.os.authz.scope_provider import ScopeAuthorizationProvider
    from agno.run.authorization import RunAuthorization, authorization_scope

    _, task = await prepare(db, remote)
    app = FastAPI()
    app.include_router(get_tasks_router(db, AgnoAPISettings()))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://company") as client:
        for scopes, status in [
            (["tasks:write"], 403),
            (["sources:publish"], 403),
            (["tasks:write", "sources:publish"], 202),
        ]:
            authority = RunAuthorization(ScopeAuthorizationProvider(), AuthorizationContext(scopes=scopes))
            with authorization_scope(lambda: authority):
                response = await client.post("/company/tasks/" + task["id"] + "/publish?attempt=1")
            assert response.status_code == status, response.text
    assert "http://company/company/tasks/" in api.pr["body"]


@pytest.mark.asyncio
async def test_required_checks_on_exact_publication_head(db, remote, api, monkeypatch):
    import agno.company.publish as publisher

    _, task = await prepare(db, remote)

    async def policy(*args):
        return {"required_checks": ["unit-tests"]}

    monkeypatch.setattr(publisher, "_policy", policy)
    for status, conclusion, sha in [
        ("queued", None, None),
        ("completed", "failure", None),
        ("completed", "success", "b" * 40),
    ]:
        api.checks = [
            {
                "id": 10,
                "name": "unit-tests",
                "status": status,
                "conclusion": conclusion,
                **({"head_sha": sha} if sha else {}),
            }
        ]
        with pytest.raises(ValueError, match="Required GitHub check"):
            await apublish_task(db, task["id"])
        assert not any("push" in args for args, _ in remote.calls)
    api.checks = [{"id": 10, "name": "unit-tests", "status": "completed", "conclusion": "success"}]
    await apublish_task(db, task["id"])
    assert api.creates == 1


@pytest.mark.asyncio
async def test_stale_publication_and_merge_cannot_overwrite_revision(db, remote, api):
    _, task = await prepare(db, remote)
    await apublish_task(db, task["id"])
    old = await _call(db, "get_task", task["id"])
    await complete(db, remote, old, 2)
    assert await _call(db, "update_task_publication", old, old["result"], verified_merge=True) is None
    assert (await _call(db, "get_task", task["id"]))["status"] == "in_review"


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [True, False])
async def test_automatic_publication_and_tick_reconcile(db, remote, api, enabled):
    import time

    from agno.company.routines import _CompanyScheduleExecutor, _policy_fingerprint
    from agno.os import CompanyConfig
    from agno.scheduler import ScheduleManager

    _, task = await prepare(db, remote)
    task = await _call(db, "transition_task", task["id"], "backlog", "Reaccept with policy")
    policy = {
        "executor_type": "agent",
        "executor_id": "engineer",
        "publish": enabled,
        "required_checks": ["unit-tests"],
        "limits": {"expires_at": int(time.time()) + 3600, "max_acceptances": 3},
    }
    schedule = await ScheduleManager(db).acreate(
        name="publisher",
        cron="0 * * * *",
        endpoint="/agents/engineer/runs",
        payload={"metadata": {"product_id": task["product_id"], "auto_accept": policy}},
        provenance={"managed_by": "company"},
    )
    task = await _call(
        db,
        "transition_task",
        task["id"],
        "ready",
        "Policy",
        executor_type="agent",
        executor_id="engineer",
        expected_updated_at=task["updated_at"],
        auto_accept={
            "routine_id": schedule.id,
            "policy": _policy_fingerprint(schedule.to_dict()),
            "max_acceptances": 3,
        },
    )
    task = await complete(db, remote, task, 2)
    api.checks = [{"id": 10, "name": "unit-tests", "status": "completed", "conclusion": "success"}]
    os = SimpleNamespace(_company_db=db, db=db, registry=None, authorization=None, company=CompanyConfig())
    executor = _CompanyScheduleExecutor(os, FastAPI(), base_url="http://company", internal_service_token="test")
    outcomes = await executor._tick()
    assert api.creates == int(enabled), outcomes
    if enabled:
        assert any(item.get("action") == "published" for item in outcomes), outcomes
        saved = await _call(db, "get_task", task["id"])
        remote.git("reset", "--hard", remote.commit)
        remote.git("fetch", str(remote.bare), saved["result"]["pr"]["branch"])
        remote.git("merge", "--no-ff", "FETCH_HEAD", "-m", "Merge task")
        merge = remote.git("rev-parse", "HEAD")
        remote.git("push", str(remote.bare), "HEAD:main")
        api.pr.update(merged=True, state="closed", merge_commit_sha=merge)
        await executor._tick()
        assert (await _call(db, "get_task", task["id"]))["status"] == "done"
    assert TOKEN not in json.dumps(await _call(db, "get_schedule", schedule.id))


@pytest.mark.asyncio
async def test_host_token_does_not_enter_run_or_sandbox(db, remote, api):
    from agno.company.sandbox import _validate_publish_environment
    from agno.run.agent import RunOutput
    from agno.run.base import RunStatus
    from agno.session.agent import AgentSession

    _, task = await prepare(db, remote)
    source = await _call(db, "get_source", task["metadata"]["checkout"]["source_id"])
    sandbox = SimpleNamespace(env={"GITHUB_READ_TOKEN": "read-only"})
    component = SimpleNamespace(sandbox=sandbox)
    _validate_publish_environment(component, source)
    output = RunOutput(
        run_id=task["job_id"],
        session_id=task["session_id"],
        status=RunStatus.completed,
        content="Changed application",
        metadata={"sandbox": {"repository": task["metadata"]["checkout"]}},
    )
    await _call(
        db,
        "upsert_session",
        AgentSession(
            session_id=task["session_id"],
            agent_id="engineer",
            runs=[output],
            created_at=task["created_at"],
            updated_at=task["updated_at"],
        ),
    )
    await _call(db, "upsert_run", output, session_id=task["session_id"])
    before = await _call(db, "get_run", task["job_id"], deserialize=False)
    assert before is not None
    await apublish_task(db, task["id"])
    after = await _call(db, "get_run", task["job_id"], deserialize=False)
    assert before == after and TOKEN not in json.dumps(after) and TOKEN not in json.dumps(sandbox.env)
    for env in ({"COMPANY_PUBLISH_TOKEN": TOKEN}, {"ALIAS": TOKEN}):
        component.sandbox.env = env
        with pytest.raises(ValueError, match="remain on the host"):
            _validate_publish_environment(component, source)


@pytest.mark.asyncio
async def test_api_failures_scrub_token_from_errors_and_logs(db, remote, api, monkeypatch, caplog):
    from agno.tools.github import GithubTools
    from agno.utils.log import logger

    _, task = await prepare(db, remote)

    def fail(*args, **kwargs):
        try:
            raise RuntimeError("denied " + TOKEN)
        except RuntimeError:
            logger.exception("request failed " + TOKEN)
            raise

    monkeypatch.setattr(GithubTools, "create_pull_request", fail)
    with pytest.raises(ValueError) as error:
        await apublish_task(db, task["id"])
    assert TOKEN not in str(error.value) + caplog.text
    assert "***" in str(error.value)


@pytest.mark.asyncio
async def test_github_async_methods_use_response_fields(remote, api):
    from agno.tools.github import GithubTools

    api.pr = json.loads((Path(__file__).parents[2] / "fixtures/github_publication.json").read_text())["pull_request"]
    remote.git("branch", api.pr["head"]["ref"], remote.commit, cwd=remote.bare)
    toolkit = GithubTools(access_token=TOKEN)
    state = json.loads(await toolkit.aget_pull_request_state("example/application", 12))
    assert state["head_sha"] == "a" * 40 and state["mergeable"] is True and state["mergeable_state"] == "clean"
    assert json.loads(await toolkit.aget_pull_request_merge_commit("example/application", 12)) == {
        "merged": False,
        "merge_commit": None,
    }
    await toolkit.aupdate_pull_request("example/application", 12, title="New", body="Updated", base="release")
    assert api.pr["title"] == "New" and api.pr["body"] == "Updated" and api.pr["base"]["ref"] == "release"
    assert json.loads(await toolkit.afind_pull_request("example/application", "company/task-1"))["number"] == 12
    api.pr.update(merged=True, merge_commit_sha="b" * 40)
    assert (
        json.loads(await toolkit.aget_pull_request_merge_commit("example/application", 12))["merge_commit"] == "b" * 40
    )
    api.checks = [{"id": 1, "name": "unit", "status": "completed", "conclusion": "success"}]
    assert json.loads(await toolkit.alist_commit_check_runs("example/application", "c" * 40))[0]["head_sha"] == "c" * 40


@pytest.mark.asyncio
async def test_crash_after_pr_creation_adopts_existing_pr(db, remote, api, monkeypatch):
    _, task = await prepare(db, remote)
    original = db.update_task_publication
    if isinstance(db, AsyncBaseDb):

        async def fail(*args, **kwargs):
            raise RuntimeError("store unavailable")
    else:

        def fail(*args, **kwargs):
            raise RuntimeError("store unavailable")

    monkeypatch.setattr(db, "update_task_publication", fail)
    with pytest.raises(RuntimeError, match="store unavailable"):
        await apublish_task(db, task["id"])
    assert api.creates == 1
    monkeypatch.setattr(db, "update_task_publication", original)
    await apublish_task(db, task["id"])
    assert api.creates == 1


@pytest.mark.asyncio
async def test_concurrent_publications_create_one_pr(db, remote, api):
    _, task = await prepare(db, remote)
    results = await asyncio.gather(apublish_task(db, task["id"]), apublish_task(db, task["id"]), return_exceptions=True)
    assert sum(isinstance(result, dict) for result in results) >= 1, results
    assert api.creates == 1
    await apublish_task(db, task["id"])
    assert api.creates == 1
