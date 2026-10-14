"""Real PostgreSQL/AgentOS execution with a deterministic model; no provider calls."""

import json
import time
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_manual import KEY, SCOPES, journey, mutation, principal, token, transition  # noqa: F401

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.job_queue import QueueConfig
from agno.models.base import Model
from agno.models.response import ModelResponse
from agno.os import AgentOS, Authorization, CompanyConfig
from agno.os.company.context import CompanyContext, current_company
from agno.os.company.policy import CompanyError
from agno.os.company.schemas import ProductCreate, TaskCreate, TaskSchedule, Transition
from agno.run import RunContext
from agno.tools.company import CompanyTools


class LocalModel(Model):
    def __init__(self):
        super().__init__(id="local-fixture", name="Local fixture", provider="test")

    def invoke(self, *args, **kwargs):
        return ModelResponse(role="assistant", content="Checked the setup guide. Fixture checks passed.")

    async def ainvoke(self, *args, **kwargs):
        return self.invoke()

    def invoke_stream(self, *args, **kwargs):
        yield self.invoke()

    async def ainvoke_stream(self, *args, **kwargs):
        yield self.invoke()

    def _parse_provider_response(self, response, **kwargs):
        return response

    def _parse_provider_response_delta(self, response, **kwargs):
        return response


def runtime_os(setup, *, hooks=None, scheduler=False):
    db, users, _ = setup
    runtime_db = PostgresDb(
        db_url=str(db.db_engine.url.render_as_string(hide_password=False)), db_schema="company_runtime_test"
    )
    with runtime_db.db_engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA IF EXISTS company_runtime_test CASCADE")
    worker = Agent(
        id="docs-agent",
        name="Documentation worker",
        model=LocalModel(),
        db=runtime_db,
        tools=[CompanyTools()],
        post_hooks=hooks or [],
    )
    os = AgentOS(
        id="company-test",
        db=runtime_db,
        agents=[worker],
        company=CompanyConfig(db=db),
        user_directory=users,
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
        queue=QueueConfig(durable=True, poll_interval=0.02),
        scheduler=scheduler,
        scheduler_poll_interval=3600,
    )
    return os, worker


def caller():
    return principal(scopes=(*SCOPES, "agents:run", "agents:read"))


def make_work(service, *, project=False):
    product = service.create_product(
        data=ProductCreate(name="Documentation", agent_id="docs-agent"), **mutation(principal=caller())
    )
    project_id = None
    if project:
        from agno.os.company.schemas import ProjectCreate

        project_id = service.create_project(
            product_id=product["id"], data=ProjectCreate(title="Improve onboarding"), **mutation()
        )["id"]
    task = service.create_task(
        product_id=product["id"],
        data=TaskCreate(
            title="Check setup guide",
            instructions="Check documented installation commands and report the evidence.",
            project_id=project_id,
        ),
        **mutation(),
    )
    return product, task


def wait_run(client, task_id, run_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"/company/v1/tasks/{task_id}/runs")
        assert response.status_code == 200, response.text
        run = next(r for r in response.json()["data"] if r["id"] == run_id)
        if run["status"] not in ("queued", "running", "dispatch_pending"):
            return run
        time.sleep(0.02)
    pytest.fail("Task run did not settle")


def test_real_queue_run_review_revision_and_restart(setup):
    os, worker = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run", "agents:read"))
        product, task = make_work(service, project=True)
        task = transition(service, task, "ready")
        headers = {"If-Match": f'"{task["version"]}"', "Idempotency-Key": "first-attempt"}
        first = client.post(f"/company/v1/tasks/{task['id']}/runs", json={}, headers=headers)
        assert first.status_code == 202, first.text
        run = first.json()
        assert (
            client.post(f"/company/v1/tasks/{task['id']}/runs", json={}, headers=headers).json()["run_id"]
            == run["run_id"]
        )
        assert wait_run(client, task["id"], run["id"])["status"] == "completed"
        task = service.get_task(task_id=task["id"], principal=caller())
        assert task["status"] == "in_review"
        task = transition(service, task, "in_progress", reason="Check the alternative setup path")
        revision = client.post(
            f"/company/v1/tasks/{task['id']}/runs",
            json={"message": "Check the alternate command too"},
            headers={"If-Match": f'"{task["version"]}"', "Idempotency-Key": "revision"},
        ).json()
        assert revision["session_id"] == run["session_id"]
        assert wait_run(client, task["id"], revision["id"])["status"] == "completed"
        output = worker.get_run_output(run_id=revision["run_id"], session_id=revision["session_id"], user_id="alice")
        assert "Fixture checks passed" in output.content
        task = service.get_task(task_id=task["id"], principal=caller())
        task = transition(
            service,
            task,
            "done",
            reason="Reviewed actual fixture result",
            acceptance_check="Result and check evidence inspected",
        )
        assert task["status"] == "done"
    # Reconstructing AgentOS keeps task history and the same underlying runtime outputs.
    restored = AgentOS(
        id="company-test",
        db=os.db,
        agents=[worker],
        company=CompanyConfig(db=setup[0]),
        user_directory=setup[1],
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
        queue=QueueConfig(durable=True, poll_interval=0.02),
    )
    with TestClient(restored.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        history = client.get(f"/company/v1/tasks/{task['id']}/runs").json()["data"]
        assert len(history) == 2 and all(r["status"] == "completed" for r in history)


def test_company_tools_identity_scope_summary_and_human_review(setup):
    _, _, service = setup
    product, project, task = journey(service)
    tools = CompanyTools()
    agent = SimpleNamespace(id="product-manager")
    context = RunContext(run_id="manager-run", session_id="manager-session", user_id="alice")
    with pytest.raises(CompanyError, match="verified"):
        tools.list_products(agent, context)
    scope = current_company.set(CompanyContext(service, principal(), product["id"]))
    try:
        created = tools.create_task(
            product["id"], "Investigate setup", "Find evidence", "unique-finding", agent, project["id"], context
        )
        assert created["origin"] == "agent" and created["status"] == "backlog"
        assert (
            tools.create_task(
                product["id"], "Investigate setup", "Find evidence", "unique-finding", agent, project["id"], context
            )["id"]
            == created["id"]
        )
        summary = tools.update_summary(
            project["id"],
            project["version"],
            "Two setup checks remain",
            {task["id"]: 1, created["id"]: 1},
            "summary",
            agent,
            context,
        )
        assert summary["instructions"] == project["instructions"] and summary["summary"] == "Two setup checks remain"
        with pytest.raises(CompanyError, match="Tasks changed"):
            tools.update_summary(project["id"], summary["version"], "Stale", {task["id"]: 1}, "stale", agent, context)
        agent_principal = replace(principal(), agent_id="agent:product-manager", product_id=product["id"])
        with pytest.raises(CompanyError, match="human"):
            service.transition_task(
                task_id=task["id"], version=1, data=Transition(to_status="ready"), **mutation(principal=agent_principal)
            )
        with pytest.raises(CompanyError):
            tools.list_work(str(uuid4()), agent, _agno_run_context=context)
        with pytest.raises(CompanyError, match="verified"):
            tools.list_products(agent, replace(context, user_id="mallory"))
        assert "transition_task" not in tools.get_functions()
    finally:
        current_company.reset(scope)
    activity = service.list_activity(principal=principal())["data"]
    assert any(a["actor_id"] == "agent:product-manager" and a["initiating_principal_id"] == "alice" for a in activity)


def test_recurring_task_schedule_adapter_pause_group_and_fresh_sessions(setup):
    from agno.db.schemas.scheduler import Schedule

    os, _ = runtime_os(setup, scheduler=True)
    service = os.company
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        product, task = make_work(service)
        task = service.set_schedule(
            task_id=task["id"],
            data=TaskSchedule(cron="0 9 * * 1-5", timezone="Europe/London"),
            version=task["version"],
            **mutation(principal=caller()),
        )
        assert task["status"] is None and task["schedule_id"]
        schedule = Schedule.from_dict(os.db.get_schedule(task["schedule_id"]))
        executor = client.app.state.scheduler_executor
        first = client.portal.call(executor.execute, schedule, os.db, False)
        assert first["status"] == "success", first
        same = client.portal.call(executor.execute, schedule, os.db, False)
        assert same["run_id"] == first["run_id"]
        schedule = replace(schedule, next_run_at=schedule.next_run_at + 86400)
        second = client.portal.call(executor.execute, schedule, os.db, False)
        assert second["status"] == "success", second
        assert second["session_id"] != first["session_id"]
        assert service.get_task(task_id=task["id"], principal=caller())["status"] is None
        assert len(service.list_tasks(principal=caller())["data"]) == 1
        paused = service.set_schedule(
            task_id=task["id"],
            data=TaskSchedule(cron="0 9 * * 1-5", timezone="Europe/London", enabled=False),
            version=task["version"],
            **mutation(principal=caller()),
        )
        assert not os.db.get_schedule(paused["schedule_id"])["enabled"]
        denied = client.portal.call(executor.execute, schedule, os.db, False)
        assert denied["status"] == "failed"


def test_schedule_validation_rejects_bad_cron_and_timezone():
    for data in ({"cron": "nonsense"}, {"cron": "0 9 * * *", "timezone": "No/SuchPlace"}):
        with pytest.raises(ValueError):
            TaskSchedule(**data)


def test_pending_dispatch_recovery_no_overlap_and_revoked_claim(setup, monkeypatch):
    os, _ = runtime_os(setup)
    service = os.company
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        product, task = make_work(service)
        runtime = service._runtime
        original = runtime._enqueue

        async def lost_dispatch(row):
            raise CompanyError(503, "test_disconnect", "Connection lost before queue acceptance")

        monkeypatch.setattr(runtime, "_enqueue", lost_dispatch)
        response = client.post(
            f"/company/v1/tasks/{task['id']}/runs", json={}, headers={"If-Match": '"1"', "Idempotency-Key": "recover"}
        )
        assert response.status_code == 503
        monkeypatch.setattr(runtime, "_enqueue", original)
        client.portal.call(runtime._recover)
        history = client.get(f"/company/v1/tasks/{task['id']}/runs").json()["data"]
        assert len(history) == 1
        assert wait_run(client, task["id"], history[0]["id"])["status"] == "completed"
        # Lost acknowledgement after durable acceptance also keeps the original run.
        replay = client.post(
            f"/company/v1/tasks/{task['id']}/runs", json={}, headers={"If-Match": '"1"', "Idempotency-Key": "recover"}
        )
        assert replay.status_code == 202 and replay.json()["id"] == history[0]["id"]
        queue = runtime.worker
        client.portal.call(queue.stop)
        pending = client.post(
            f"/company/v1/tasks/{task['id']}/runs", json={}, headers={"If-Match": '"1"', "Idempotency-Key": "pending"}
        ).json()
        overlap = client.post(
            f"/company/v1/tasks/{task['id']}/runs", json={}, headers={"If-Match": '"1"', "Idempotency-Key": "overlap"}
        )
        assert overlap.status_code == 409 and overlap.json()["error"]["code"] == "run_active"
        skipped = client.portal.call(
            lambda: service.arun_task(
                principal=caller(),
                task_id=task["id"],
                version=1,
                idempotency_key="scheduled-overlap",
                trigger="schedule",
            )
        )
        assert skipped["status"] == "skipped" and skipped["run_id"] is None
        setup[1].set_disabled("alice", True)
        client.portal.call(queue.start)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = client.portal.call(queue.store.get_job, pending["id"])
            if job["status"] == "failed":
                break
            time.sleep(0.02)
        assert job["status"] == "failed" and "active" in job["error"]
        setup[1].set_disabled("alice", False)
        assert wait_run(client, task["id"], pending["id"])["status"] == "failed"
        assert service.get_task(task_id=task["id"], principal=caller())["status"] is None


def test_queue_cancel_preserves_business_work(setup):
    os, _ = runtime_os(setup)
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        service = os.company
        _, task = make_work(service, project=True)
        task = transition(service, task, "ready")
        client.portal.call(service._runtime.worker.stop)
        result = client.post(
            f"/company/v1/tasks/{task['id']}/runs",
            json={},
            headers={"If-Match": f'"{task["version"]}"', "Idempotency-Key": "cancel-me"},
        ).json()
        canceled = client.post(f"/company/v1/tasks/{task['id']}/runs/{result['id']}/cancel")
        assert canceled.status_code == 200, canceled.text
        assert canceled.json()["status"] == "cancelled"
        assert service.get_task(task_id=task["id"], principal=caller())["status"] == "in_progress"


def test_housekeeping_uses_worker_context_and_preserves_human_plan(setup):
    created = []

    def housekeeping(agent, run_context):
        context = current_company.get()
        tools = CompanyTools()
        project = tools.list_work(context.product_id, agent, _agno_run_context=run_context)["projects"]["data"][0]
        draft = tools.create_task(
            context.product_id,
            "Fix setup example",
            "Check the command against a clean environment",
            "finding-setup-1",
            agent,
            str(project["id"]),
            run_context,
        )
        created.append(draft["id"])
        tasks = tools.list_work(context.product_id, agent, str(project["id"]), run_context)["tasks"]["data"]
        tools.update_summary(
            str(project["id"]),
            project["version"],
            "One setup issue needs investigation",
            {str(t["id"]): t["version"] for t in tasks},
            "summary-setup-1",
            agent,
            run_context,
        )

    os, _ = runtime_os(setup, hooks=[housekeeping])
    from agno.os.company.schemas import ProjectCreate

    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        service = os.company
        product, task = make_work(service)
        project = service.create_project(
            product_id=product["id"],
            data=ProjectCreate(title="Onboarding", instructions="Preserve this human plan"),
            **mutation(),
        )
        response = client.post(
            f"/company/v1/tasks/{task['id']}/runs",
            json={},
            headers={"If-Match": '"1"', "Idempotency-Key": "housekeeping"},
        )
        assert response.status_code == 202, response.text
        assert wait_run(client, task["id"], response.json()["id"])["status"] == "completed"
        assert len(created) == 1
        fresh = service.get_project(project_id=project["id"], principal=caller())
        assert fresh["instructions"] == "Preserve this human plan"
        assert fresh["summary"] == "One setup issue needs investigation"
        assert fresh["counts"]["backlog"] == 1


def test_manager_team_delegates_company_tools_with_verified_identity(setup, tmp_path):
    platform = pytest.importorskip(
        "agno.os.platform", reason="Run this compatibility test with the manager workstream combined"
    )

    class DelegateModel(LocalModel):
        def invoke(self, messages, **kwargs):
            tools = [t["function"]["name"] for t in kwargs.get("tools", []) or []]
            responses = [m for m in messages if m.role == "tool"]
            if responses:
                return ModelResponse(role="assistant", content=str(responses[-1].content))
            name = "delegate_task_to_member" if "delegate_task_to_member" in tools else "list_products"
            arguments = (
                {"member_id": "product-manager", "task": "List the Company Products"}
                if name == "delegate_task_to_member"
                else {}
            )
            return ModelResponse(
                role="assistant",
                tool_calls=[
                    {
                        "id": str(uuid4()),
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(arguments)},
                    }
                ],
            )

        async def ainvoke(self, *args, **kwargs):
            return self.invoke(*args, **kwargs)

    db, users, service = setup
    service.create_product(data=ProductCreate(name="Documentation"), **mutation())
    product_manager = Agent(
        id="product-manager",
        name="Product Manager",
        role="Manage Company Products, Projects and Tasks",
        model=DelegateModel(),
        tools=[CompanyTools()],
    )
    os = AgentOS(
        id="company-test",
        agents=[product_manager],
        db=db,
        company=CompanyConfig(db=db),
        user_directory=users,
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
        manager=platform.ManagerConfig(model=DelegateModel(), workspace=str(tmp_path)),
        queue=QueueConfig(durable=True, poll_interval=0.02),
    )
    os.manager.members.append(product_manager)
    assert {m.id for m in os.manager.members} == {
        "platform-manager",
        "platform-builder",
        "platform-engineer",
        "product-manager",
    }
    assert all(t.name == "company" for t in product_manager.tools)
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "teams:run", "agents:run"))
        response = client.post(
            f"/teams/{os.manager.id}/runs", data={"message": "List the Company Products", "stream": "false"}
        )
        assert response.status_code == 200, response.text
        assert "Documentation" in response.json()["content"], response.text
        background = client.post(
            f"/teams/{os.manager.id}/runs",
            data={"message": "List the Company Products", "stream": "false", "background": "true"},
        )
        assert background.status_code == 202, background.text
        body = background.json()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            output = os.manager.get_run_output(run_id=body["run_id"], session_id=body["session_id"], user_id="alice")
            if output and getattr(output.status, "value", None) == "COMPLETED":
                break
            time.sleep(0.02)
        assert output and "Documentation" in str(output.content)
        client.headers["Authorization"] = "Bearer " + token(who="mallory", scopes=(*SCOPES, "teams:run", "agents:run"))
        denied = client.post(
            f"/teams/{os.manager.id}/runs",
            data={"message": "List the Company Products", "stream": "false", "user_id": "alice"},
        )
        assert denied.status_code == 200, denied.text
        assert "Documentation" not in denied.json()["content"]


def test_v2_upgrade_preserves_prose_history_and_direct_work(setup):
    from sqlalchemy import text

    from agno.os.company.migrations import migrate
    from agno.os.company.migrations.v001 import SQL as v1
    from agno.os.company.migrations.v002 import SQL as v2

    db, _, service = setup
    product, project, task = str(uuid4()), str(uuid4()), str(uuid4())
    with db.db_engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA agno_company CASCADE")
        conn.exec_driver_sql(v1)
        conn.exec_driver_sql(v2)
        conn.execute(
            text(
                "INSERT INTO agno_company.products(id,key,name,purpose,owner_id) VALUES (:id,'PRD-1','Docs','Reliable guidance','alice')"
            ),
            {"id": product},
        )
        conn.execute(
            text(
                "INSERT INTO agno_company.product_memberships(product_id,principal_id,role) VALUES (:id,'alice','owner')"
            ),
            {"id": product},
        )
        conn.execute(
            text(
                "INSERT INTO agno_company.projects(id,key,product_id,title,outcome,acceptance_criteria,owner_id,status) VALUES (:id,'PRJ-2',:pid,'Onboarding','Install succeeds','Test a clean install','alice','canceled')"
            ),
            {"id": project, "pid": product},
        )
        conn.execute(
            text(
                "INSERT INTO agno_company.tasks(id,key,product_id,title,description,acceptance_criteria,accountable_owner_id,status) VALUES (:id,'TSK-3',:pid,'Check guide','Find broken commands','Link evidence','alice','canceled')"
            ),
            {"id": task, "pid": product},
        )
        conn.execute(
            text(
                "INSERT INTO agno_company.comments(id,task_id,author_id,body) VALUES (:id,:task,'alice','Keep this history')"
            ),
            {"id": str(uuid4()), "task": task},
        )
    migrate(db)
    migrate(db)
    preserved = service.get_project(principal=principal(), project_id=project)
    assert preserved["state"] == "archived" and preserved["status"] == "empty"
    assert "Install succeeds" in preserved["instructions"] and "Test a clean install" in preserved["instructions"]
    direct = service.get_task(principal=principal(), task_id=task)
    assert direct["status"] is None and direct["state"] == "archived"
    assert "Find broken commands" in direct["instructions"] and "Link evidence" in direct["instructions"]
    assert (
        service.list_comments(principal=principal(), kind="task", record_id=task)["data"][0]["body"]
        == "Keep this history"
    )


def test_codex_adapter_task_revision_keeps_native_thread_and_explicit_workspace(setup, tmp_path, monkeypatch):
    import subprocess

    from agno.agents.codex import CodexAgent
    from tests.unit.agents.test_codex import _agent_message, _turn_completed, fake_sdk

    sdk = fake_sdk.__wrapped__(monkeypatch)
    sdk.final_response = "Fixture adapter result; no live coding model was invoked."
    sdk.notifications = [_agent_message("answer", sdk.final_response, phase="final_answer"), _turn_completed()]
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    (source / "guide.md").write_text("Check the installation command.\n")
    subprocess.run(["git", "-C", str(source), "add", "guide.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "user.name=Company fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    workspace = tmp_path / "task-worktree"
    subprocess.run(
        ["git", "-C", str(source), "worktree", "add", "--detach", str(workspace), "HEAD"],
        check=True,
        capture_output=True,
    )
    db, users, _ = setup
    coder = CodexAgent(id="docs-agent", db=db, cwd=str(workspace), sandbox="workspace-write", approval_mode="deny_all")
    os = AgentOS(
        id="company-test",
        db=db,
        agents=[coder],
        company=CompanyConfig(db=db),
        user_directory=users,
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
        queue=QueueConfig(durable=True, poll_interval=0.02),
    )
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        _, task = make_work(os.company, project=True)
        task = transition(os.company, task, "ready")
        first = client.post(
            f"/company/v1/tasks/{task['id']}/runs",
            json={},
            headers={"If-Match": f'"{task["version"]}"', "Idempotency-Key": "codex-first"},
        )
        assert first.status_code == 202, first.text
        assert wait_run(client, task["id"], first.json()["id"])["status"] == "completed"
        task = os.company.get_task(principal=caller(), task_id=task["id"])
        task = transition(os.company, task, "in_progress", reason="Revise the evidence")
        second = client.post(
            f"/company/v1/tasks/{task['id']}/runs",
            json={"message": "Recheck the command"},
            headers={"If-Match": f'"{task["version"]}"', "Idempotency-Key": "codex-revision"},
        )
        assert second.status_code == 202, second.text
        assert wait_run(client, task["id"], second.json()["id"])["status"] == "completed"
        assert first.json()["session_id"] == second.json()["session_id"]
        result = client.get(second.json()["result_url"])
        assert "no live coding model" in result.json()["content"]
    starts = [c for c in sdk.calls if c["op"] == "thread_start"]
    resumes = [c for c in sdk.calls if c["op"] == "thread_resume"]
    assert len(starts) == 1 and len(resumes) == 1
    assert starts[0]["thread_id"] == resumes[0]["thread_id"]
    assert starts[0]["kwargs"]["cwd"] == str(workspace)
    assert subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True) == ""


def test_schedule_downtime_grouping_and_previous_result(setup):
    from agno.db.schemas.scheduler import Schedule
    from agno.os.company.schemas import ProjectCreate, TaskPatch

    os, _ = runtime_os(setup, scheduler=True)
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        service = os.company
        product, task = make_work(service)
        task = service.set_schedule(
            task_id=task["id"],
            version=1,
            data=TaskSchedule(cron="0 9 * * *", timezone="Europe/London"),
            **mutation(principal=caller()),
        )
        project = service.create_project(product_id=product["id"], data=ProjectCreate(title="Follow up"), **mutation())
        with pytest.raises(CompanyError, match="Pause"):
            service.update_task(
                task_id=task["id"], version=task["version"], data=TaskPatch(project_id=project["id"]), **mutation()
            )
        due = int(time.time()) - 7 * 86400
        os.db.update_schedule(task["schedule_id"], next_run_at=due)
        client.portal.call(service._runtime._recover)
        assert os.db.get_schedule(task["schedule_id"])["next_run_at"] == due
        schedule = Schedule.from_dict(os.db.get_schedule(task["schedule_id"]))
        first = client.portal.call(client.app.state.scheduler_executor.execute, schedule, os.db)
        assert first["status"] == "success", first
        assert os.db.get_schedule(task["schedule_id"])["next_run_at"] > int(time.time())
        assert len(client.get(f"/company/v1/tasks/{task['id']}/runs").json()["data"]) == 1
        second = client.post(
            f"/company/v1/tasks/{task['id']}/runs",
            json={},
            headers={"If-Match": f'"{task["version"]}"', "Idempotency-Key": "manual-after-schedule"},
        ).json()
        assert wait_run(client, task["id"], second["id"])["status"] == "completed"
        job = client.portal.call(service._runtime.worker.store.get_job, second["id"])
        assert "Fixture checks passed" in json.loads(job["payload"]["input"])["previous_result"]
        paused = service.set_schedule(
            task_id=task["id"],
            version=task["version"],
            data=TaskSchedule(cron="0 9 * * *", timezone="Europe/London", enabled=False),
            **mutation(principal=caller()),
        )
        grouped = service.update_task(
            task_id=task["id"], version=paused["version"], data=TaskPatch(project_id=project["id"]), **mutation()
        )
        assert grouped["status"] == "backlog"
        assert len(client.get(f"/company/v1/tasks/{task['id']}/runs").json()["data"]) == 2


def test_company_tool_schemas_exclude_identity_and_execution_context():
    tools = CompanyTools()
    for function in tools.get_functions().values():
        function.process_entrypoint()
        properties = function.parameters.get("properties", {})
        assert not {"agent", "_agno_run_context", "principal", "user_id", "scopes", "claims"}.intersection(properties)


def test_simultaneous_dispatch_has_one_runtime_ticket(setup):
    from concurrent.futures import ThreadPoolExecutor

    os, _ = runtime_os(setup)
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        _, task = make_work(os.company)

        def submit():
            response = client.post(
                f"/company/v1/tasks/{task['id']}/runs",
                json={},
                headers={"If-Match": '"1"', "Idempotency-Key": "simultaneous"},
            )
            assert response.status_code == 202, response.text
            return response.json()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        assert results[0]["id"] == results[1]["id"]
        assert wait_run(client, task["id"], results[0]["id"])["status"] == "completed"
        assert len(client.get(f"/company/v1/tasks/{task['id']}/runs").json()["data"]) == 1


def test_cancel_interrupts_executing_task(setup):
    import asyncio
    import threading

    started = threading.Event()
    release = threading.Event()

    async def hold_execution(**kwargs):
        started.set()
        while not release.is_set():
            await asyncio.sleep(0.02)

    os, _ = runtime_os(setup)
    os.agents[0].pre_hooks = [hold_execution]
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        _, task = make_work(os.company, project=True)
        task = transition(os.company, task, "ready")
        response = client.post(
            f"/company/v1/tasks/{task['id']}/runs",
            json={},
            headers={"If-Match": json.dumps(str(task["version"])), "Idempotency-Key": "active-cancel"},
        )
        assert response.status_code == 202, response.text
        run = response.json()
        try:
            assert started.wait(5), "Worker did not reach execution"
            cancelled = client.post(f"/company/v1/tasks/{task['id']}/runs/{run['id']}/cancel")
            assert cancelled.status_code == 200, cancelled.text
        finally:
            release.set()
        assert wait_run(client, task["id"], run["id"])["status"] == "cancelled"
        assert os.company.get_task(task_id=task["id"], principal=caller())["status"] == "in_progress"


def test_cancel_pending_dispatch_survives_recovery_and_retry(setup, monkeypatch):
    os, _ = runtime_os(setup)
    with TestClient(os.get_app()) as client:
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        _, task = make_work(os.company)
        runtime = os.company._runtime
        enqueue = runtime._enqueue

        async def fail_dispatch(row):
            raise CompanyError(503, "lost_dispatch", "Queue unavailable before acceptance")

        monkeypatch.setattr(runtime, "_enqueue", fail_dispatch)
        headers = {"If-Match": json.dumps(str(task["version"])), "Idempotency-Key": "cancel-pending"}
        response = client.post(f"/company/v1/tasks/{task['id']}/runs", json={}, headers=headers)
        assert response.status_code == 503
        run = client.get(f"/company/v1/tasks/{task['id']}/runs").json()["data"][0]
        # A deployment may remove the worker before this interrupted dispatch is cancelled.
        registered = os.agents
        os.agents = []
        cancelled = client.post(f"/company/v1/tasks/{task['id']}/runs/{run['id']}/cancel")
        assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
        monkeypatch.setattr(runtime, "_enqueue", enqueue)
        client.portal.call(runtime._recover)
        os.agents = registered
        replay = client.post(f"/company/v1/tasks/{task['id']}/runs", json={}, headers=headers)
        assert replay.status_code == 202 and replay.json()["status"] == "cancelled"
        assert client.portal.call(runtime.worker.store.get_job, run["id"]) is None
        # A new, explicit request can proceed after cancellation.
        fresh = client.post(
            f"/company/v1/tasks/{task['id']}/runs", json={}, headers={**headers, "Idempotency-Key": "after-cancel"}
        )
        assert fresh.status_code == 202, fresh.text
        assert wait_run(client, task["id"], fresh.json()["id"])["status"] == "completed"
