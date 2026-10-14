"""Scheduler/queue/approval integration with real PostgreSQL and mocked GitHub HTTP."""

import asyncio
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from test_execution import caller, make_work, runtime_os
from test_manual import KEY, SCOPES, journey, mutation, principal, token, transition

from agno.os import AgentOS, Authorization, CompanyConfig, QueueConfig
from agno.os.company import review
from agno.os.company.migrations import migrate
from agno.os.company.policy import CompanyError
from agno.os.company.runtime import CompanyRuntime
from agno.os.company.schemas import PullRequestReview, TaskPatch, Transition

URL = "https://github.com/example/docs/pull/42"
SHA = "a" * 40


def accept_ready(service, task, who=None):
    return service.transition_task(
        task_id=task["id"],
        version=task["version"],
        data=Transition(to_status="ready"),
        **mutation(principal=who or caller()),
    )


def wait_status(service, task, status):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        current = service.get_task(principal=caller(), task_id=task["id"])
        if current["status"] == status:
            return current
        time.sleep(0.02)
    pytest.fail(f"Task did not reach {status}: {current}")


def tick(client, service):
    client.portal.call(service._runtime._tick)


def link_pr(service, task):
    return service.set_review_pull_request(
        task_id=task["id"],
        version=task["version"],
        data=PullRequestReview(url=URL, head_sha=SHA),
        **mutation(principal=caller()),
    )


def github_response(**overrides):
    return {
        "number": 42,
        "html_url": URL,
        "base": {"repo": {"full_name": "example/docs"}},
        "head": {"sha": SHA},
        "state": "closed",
        "merged": True,
        "merged_by": {"id": 123, "login": "reviewer", "type": "User"},
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "merge_commit_sha": "b" * 40,
        **overrides,
    }


def mock_github(monkeypatch, response, code=200):
    requests = []
    original = httpx.AsyncClient

    def handle(request):
        requests.append(request)
        return httpx.Response(code, json=response)

    transport = httpx.MockTransport(handle)
    monkeypatch.setattr(review.httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs))
    return requests


def review_task(client, service):
    _, task = make_work(service, project=True)
    task = accept_ready(service, task)
    tick(client, service)
    return wait_status(service, task, "in_review")


def test_scheduler_automatically_runs_ready_and_waits_for_human(setup):
    os, _ = runtime_os(setup, scheduler=True)
    os._scheduler_poll_interval = 1
    service = os.company
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        _, task = make_work(service, project=True)
        response = client.post(
            f"/company/v1/tasks/{task['id']}/transitions",
            json={"to_status": "ready"},
            headers={"Idempotency-Key": "ready", "If-Match": f'"{task["version"]}"'},
        )
        assert response.status_code == 200, response.text
        task = wait_status(service, task, "in_review")
        tick(client, service)
        assert service.get_task(principal=caller(), task_id=task["id"])["status"] == "in_review"
        runs = service.list_runs(principal=caller(), task_id=task["id"])["data"]
        assert len(runs) == 1 and runs[0]["trigger"] == "ready" and runs[0]["status"] == "completed"
        assert "ready_principal" not in response.json()
        done = transition(service, task, "done", reason="Human checked the result", acceptance_check="Checks passed")
        assert done["status"] == "done"


def test_concurrent_ticks_and_restart_do_not_duplicate_ready_execution(setup):
    os, worker = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        _, task = make_work(service, project=True)
        task = accept_ready(service, task)
        second = CompanyRuntime(service, os)
        second.app, second.worker = service._runtime.app, service._runtime.worker

        async def race():
            await asyncio.gather(service._runtime._tick(), second._tick())

        client.portal.call(race)
        wait_status(service, task, "in_review")
        tick(client, service)
        assert len(service.list_runs(principal=caller(), task_id=task["id"])["data"]) == 1
        _, pending = make_work(service, project=True)
        pending = accept_ready(service, pending)
    restored = AgentOS(
        id="company-test",
        db=os.db,
        agents=[worker],
        company=CompanyConfig(db=setup[0]),
        user_directory=setup[1],
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
        queue=QueueConfig(durable=True, poll_interval=0.02),
        scheduler=True,
        scheduler_poll_interval=1,
    )
    with TestClient(restored.get_app()):
        wait_status(restored.company, pending, "in_review")
        assert len(restored.company.list_runs(principal=caller(), task_id=task["id"])["data"]) == 1
        assert len(restored.company.list_runs(principal=caller(), task_id=pending["id"])["data"]) == 1


@pytest.mark.parametrize("block", ["disabled", "membership", "scope", "archive", "worker"])
def test_ready_rechecks_authority_and_never_substitutes_a_worker(setup, block):
    os, _ = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        product, task = make_work(service, project=True)
        task = accept_ready(service, task, principal() if block == "scope" else caller())
        with setup[0].db_engine.begin() as conn:
            if block == "membership":
                conn.execute(
                    text(
                        "INSERT INTO agno_company.product_memberships(product_id,principal_id,role) VALUES(:id,'bob','owner')"
                    ),
                    {"id": product["id"]},
                )
                conn.execute(
                    text("UPDATE agno_company.products SET owner_id='bob' WHERE id=:id"), {"id": product["id"]}
                )
                conn.execute(
                    text(
                        "UPDATE agno_company.product_memberships SET active=false WHERE product_id=:id AND principal_id='alice'"
                    ),
                    {"id": product["id"]},
                )
            elif block == "archive":
                conn.execute(
                    text("UPDATE agno_company.projects SET state='archived' WHERE id=:id"), {"id": task["project_id"]}
                )
            elif block == "worker":
                conn.execute(
                    text("UPDATE agno_company.products SET agent_id='other-agent' WHERE id=:id"), {"id": product["id"]}
                )
        if block == "disabled":
            setup[1].set_disabled("alice", True)
        tick(client, service)
        with setup[0].db_engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT status,automation_error FROM agno_company.tasks WHERE id=:id"), {"id": task["id"]}
                )
                .mappings()
                .one()
            )
            assert row["status"] == "ready"
            if block != "archive":
                assert row["automation_error"]
            assert conn.execute(text("SELECT count(*) FROM agno_company.task_runs")).scalar() == 0


def test_ready_execution_change_requires_renewed_acceptance(setup):
    os, _ = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        _, task = make_work(service, project=True)
        task = accept_ready(service, task)
        task = service.update_task(
            task_id=task["id"],
            version=task["version"],
            data=TaskPatch(instructions="Different work"),
            **mutation(principal=caller()),
        )
        assert task["status"] == "backlog" and task["accepted_by"] is None
        tick(client, service)
        assert service.list_runs(principal=caller(), task_id=task["id"])["data"] == []
        accept_ready(service, task)
        tick(client, service)
        wait_status(service, task, "in_review")


def test_partial_ready_dispatch_recovers_but_cancellation_does_not_retry(setup, monkeypatch):
    os, _ = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        _, task = make_work(service, project=True)
        accept_ready(service, task)
        enqueue = service._runtime._enqueue

        async def interrupted(row):
            raise CompanyError(503, "interrupted", "Queue temporarily unavailable")

        monkeypatch.setattr(service._runtime, "_enqueue", interrupted)
        tick(client, service)
        runs = service.list_runs(principal=caller(), task_id=task["id"])["data"]
        assert len(runs) == 1 and runs[0]["status"] == "dispatch_pending"
        monkeypatch.setattr(service._runtime, "_enqueue", enqueue)
        tick(client, service)
        wait_status(service, task, "in_review")
        assert len(service.list_runs(principal=caller(), task_id=task["id"])["data"]) == 1
        _, cancel = make_work(service, project=True)
        accept_ready(service, cancel)
        monkeypatch.setattr(service._runtime, "_enqueue", interrupted)
        tick(client, service)
        run = service.list_runs(principal=caller(), task_id=cancel["id"])["data"][0]
        client.portal.call(lambda: service.acancel_task_run(principal=caller(), task_id=cancel["id"], run_id=run["id"]))
        monkeypatch.setattr(service._runtime, "_enqueue", enqueue)
        tick(client, service)
        tick(client, service)
        assert service.get_task(principal=caller(), task_id=cancel["id"])["status"] == "in_progress"
        runs = service.list_runs(principal=caller(), task_id=cancel["id"])["data"]
        assert len(runs) == 1 and runs[0]["status"] == "cancelled"


def test_pr_link_is_human_review_only_and_merge_is_audited_once(setup, monkeypatch):
    os, _ = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        task = review_task(client, service)
        with pytest.raises(CompanyError, match="human"):
            service.set_review_pull_request(
                task_id=task["id"],
                version=task["version"],
                data=PullRequestReview(url=URL, head_sha=SHA),
                **mutation(principal=replace(caller(), agent_id="agent:product-manager")),
            )
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        response = client.put(
            f"/company/v1/tasks/{task['id']}/review/pull-request",
            json={"url": URL, "head_sha": SHA},
            headers={"Idempotency-Key": "link", "If-Match": f'"{task["version"]}"'},
        )
        assert response.status_code == 200, response.text
        assert response.json()["review_pull_request"] == {"url": URL, "head_sha": SHA}
        assert "review_principal" not in response.json()
        body = github_response()
        calls = mock_github(monkeypatch, body)

        async def duplicate():
            await asyncio.gather(service._runtime._tick(), service._runtime._tick())

        client.portal.call(duplicate)
        task = wait_status(service, task, "done")
        tick(client, service)
        assert str(calls[0].url) == "https://api.github.com/repos/example/docs/pulls/42"
        assert service.get_project(principal=caller(), project_id=task["project_id"])["status"] == "completed"
        events = [
            e for e in service.list_activity(principal=caller())["data"] if e["operation"] == "task.pull_request_merged"
        ]
        assert len(events) == 1 and events[0]["actor_id"] == "service:github"
        assert events[0]["initiating_principal_id"] == "alice"
        assert events[0]["delta"]["verification"]["head_sha"] == SHA
        assert events[0]["delta"]["verification"]["merged_by"]["login"] == "reviewer"


@pytest.mark.parametrize("case", ["open", "closed", "changed", "bot", "old", "unavailable", "wrong_repo", "malformed"])
def test_unverified_pr_never_completes_task(setup, monkeypatch, case):
    os, _ = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        task = link_pr(service, review_task(client, service))
        body = github_response()
        code = 200
        if case == "open":
            body.update(merged=False, state="open")
        elif case == "closed":
            body["merged"] = False
        elif case == "changed":
            body["head"]["sha"] = "c" * 40
        elif case == "bot":
            body["merged_by"]["type"] = "Bot"
        elif case == "old":
            body["merged_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        elif case == "unavailable":
            code = 403
            body = {"message": "SENSITIVE PROVIDER ERROR"}
        elif case == "wrong_repo":
            body["base"]["repo"]["full_name"] = "other/docs"
        elif case == "malformed":
            body["merged_by"] = None
        mock_github(monkeypatch, body, code)
        tick(client, service)
        task = service.get_task(principal=caller(), task_id=task["id"])
        assert task["status"] == "in_review"
        assert bool(task["automation_error"]) == (case != "open")
        assert "SENSITIVE" not in str(task)
        # The explicit human acceptance path remains available even if GitHub is unavailable.
        done = transition(service, task, "done", reason="Inspected work", acceptance_check="Approved by human")
        assert done["status"] == "done"


def test_review_revision_and_revocation_races_cannot_accept_stale_proof(setup, monkeypatch):
    os, _ = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        task = link_pr(service, review_task(client, service))

        async def revision_during_verification(*args):
            service.transition_task(
                task_id=task["id"],
                version=task["version"],
                data=Transition(to_status="in_progress", reason="Needs revision"),
                **mutation(principal=caller()),
            )
            return github_response()

        monkeypatch.setattr(review, "_verify_merge", revision_during_verification)
        tick(client, service)
        current = service.get_task(principal=caller(), task_id=task["id"])
        assert current["status"] == "in_progress" and current["review_pull_request"] is None
        task = transition(service, current, "in_review")
        task = link_pr(service, task)

        async def revoke_during_verification(*args):
            with setup[0].db_engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO agno_company.product_memberships(product_id,principal_id,role) VALUES(:id,'bob','owner')"
                    ),
                    {"id": task["product_id"]},
                )
                conn.execute(
                    text("UPDATE agno_company.products SET owner_id='bob' WHERE id=:id"), {"id": task["product_id"]}
                )
                conn.execute(
                    text(
                        "UPDATE agno_company.product_memberships SET role='reader' WHERE product_id=:id AND principal_id='alice'"
                    ),
                    {"id": task["product_id"]},
                )
            return github_response()

        monkeypatch.setattr(review, "_verify_merge", revoke_during_verification)
        tick(client, service)
        assert service.get_task(principal=caller(), task_id=task["id"])["status"] == "in_review"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/example/docs/pull/42",
        "https://evil.test/a/b/pull/42",
        "https://github.com@example.com/a/b/pull/42",
        URL + "?token=x",
        URL + "/../43",
    ],
)
def test_review_url_cannot_redirect_credentials(url):
    with pytest.raises(ValidationError):
        PullRequestReview(url=url, head_sha=SHA)


def test_v5_upgrade_does_not_silently_run_legacy_ready_tasks(setup):
    db, _, service = setup
    _, _, task = journey(service)
    task = transition(service, task, "ready")
    with db.db_engine.begin() as conn:
        for name in (
            "ready_principal",
            "ready_agent_id",
            "review_pull_request",
            "review_principal",
            "review_started_at",
            "automation_error",
        ):
            conn.exec_driver_sql("ALTER TABLE agno_company.tasks DROP COLUMN " + name)
        conn.exec_driver_sql("DELETE FROM agno_company.schema_version WHERE version=6")
    migrate(db)
    migrate(db)
    current = service.get_task(principal=principal(), task_id=task["id"])
    assert current["status"] == "ready" and current["version"] == task["version"]
    with db.db_engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT ready_principal FROM agno_company.tasks WHERE id=:id"), {"id": task["id"]}
            ).scalar()
            is None
        )


def test_failed_ready_run_requires_deliberate_retry(setup, monkeypatch):
    os, worker = runtime_os(setup)
    service = os.company

    async def fail(*args, **kwargs):
        raise RuntimeError("Fixture worker failure")

    monkeypatch.setattr(worker.model, "ainvoke", fail)
    with TestClient(os.get_app()) as client:
        _, task = make_work(service, project=True)
        accept_ready(service, task)
        tick(client, service)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            runs = service.list_runs(principal=caller(), task_id=task["id"])["data"]
            if runs and runs[0]["status"] == "failed":
                break
            time.sleep(0.02)
        assert runs[0]["status"] == "failed"
        tick(client, service)
        assert service.get_task(principal=caller(), task_id=task["id"])["status"] == "in_progress"
        assert len(service.list_runs(principal=caller(), task_id=task["id"])["data"]) == 1


def test_ready_progression_composes_with_manager(setup, tmp_path):
    import agno.os as os_module

    manager_config = getattr(os_module, "ManagerConfig", None)
    if manager_config is None:
        pytest.skip("Combine with Manager to test composition")
    from test_execution import LocalModel

    original, worker = runtime_os(setup)
    os = AgentOS(
        id="company-test",
        db=original.db,
        agents=[worker],
        company=CompanyConfig(db=setup[0], model=LocalModel()),
        user_directory=setup[1],
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
        manager=manager_config(model=LocalModel(), workspace=str(tmp_path)),
        queue=QueueConfig(durable=True, poll_interval=0.02),
        scheduler=True,
        scheduler_poll_interval=1,
    )
    product_manager = os.company.product_manager
    assert product_manager is not None
    assert {m.id for m in os.manager.members} == {
        "platform-manager",
        "platform-builder",
        "platform-engineer",
        "product-manager",
    }
    app = os.get_app()
    os.resync(app)
    os.resync(app)
    assert sum(member is product_manager for member in os.manager.members) == 1
    assert sum(agent is product_manager for agent in os.agents) == 1
    with TestClient(app):
        _, task = make_work(os.company, project=True)
        accept_ready(os.company, task)
        task = wait_status(os.company, task, "in_review")
        assert "link_pull_request" in task["permitted_actions"]
        assert "set_review_pull_request" not in product_manager.tools[0].get_functions()


@pytest.mark.asyncio
async def test_github_token_stays_on_fixed_api_host_and_redirects_fail_closed(monkeypatch):
    requests = mock_github(monkeypatch, {"message": "redirect"}, 302)
    with pytest.raises(CompanyError, match="Could not verify"):
        await review._verify_merge({"url": URL, "head_sha": SHA}, datetime.now(timezone.utc), "test-only-secret")
    assert len(requests) == 1
    assert requests[0].url.host == "api.github.com"
    assert requests[0].headers["Authorization"] == "Bearer test-only-secret"


def test_plain_evidence_link_cannot_trigger_completion(setup, monkeypatch):
    from agno.os.company.schemas import Evidence

    os, _ = runtime_os(setup)
    with TestClient(os.get_app()) as client:
        task = review_task(client, os.company)
        task = transition(os.company, task, "in_progress", reason="Add evidence")
        task = os.company.update_task(
            task_id=task["id"],
            version=task["version"],
            data=TaskPatch(evidence=[Evidence(url=URL)]),
            **mutation(principal=caller()),
        )
        task = transition(os.company, task, "in_review")
        calls = mock_github(monkeypatch, github_response())
        tick(client, os.company)
        assert not calls
        assert os.company.get_task(principal=caller(), task_id=task["id"])["status"] == "in_review"


@pytest.mark.asyncio
async def test_merge_commit_metadata_is_optional_but_head_is_verified(monkeypatch):
    payload = github_response()
    del payload["merge_commit_sha"]
    mock_github(monkeypatch, payload)
    proof = await review._verify_merge({"url": URL, "head_sha": SHA}, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert proof["head_sha"] == SHA and proof["merge_commit_sha"] is None
