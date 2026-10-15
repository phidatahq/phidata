"""Authenticated Product setup, delegated planning and pinned engineering work."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_execution import caller, runtime_os
from test_manual import mutation, principal

from agno.os.company.context import CompanyContext, current_company
from agno.os.company.policy import CompanyError
from agno.os.company.schemas import CompanySetup, ProductCreate, ProductPatch, Repository
from agno.run import RunContext
from agno.tools.company import CompanyTools


def test_setup_is_explicit_owned_once_and_does_not_reset_configuration(setup):
    _, _, service = setup
    assert service.list_products(principal=principal())["data"] == []
    data = CompanySetup(repository=Repository(url="https://github.com/example/application"))

    def create():
        return service.setup_agentos(data=data, **mutation())

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: create(), range(2)))
    assert first["id"] == second["id"]
    assert first["builtin"] == "agentos" and first["owner_id"] == "alice"
    changed = service.update_product(
        product_id=first["id"], version=first["version"], data=ProductPatch(name="Our AgentOS"), **mutation()
    )
    again = asyncio.run(service.asetup_agentos(data=CompanySetup(), **mutation()))
    assert again["name"] == "Our AgentOS" and again["version"] == changed["version"]
    with pytest.raises(CompanyError):
        service.setup_agentos(data=data, **mutation(principal=principal("bob")))


def test_product_manager_can_create_owned_product_but_not_assign_authority(setup):
    service = setup[2]
    tools = CompanyTools()
    context = current_company.set(CompanyContext(service, principal()))
    try:
        created = tools.create_product(
            "Website",
            "Maintain our site",
            "website",
            SimpleNamespace(id="product-manager-internal"),
            RunContext(run_id="test", session_id="test", user_id="alice"),
        )
    finally:
        current_company.reset(context)
    assert created["owner_id"] == "alice" and created["agent_id"] is None
    delegated = replace(principal(), agent_id="agent:product-manager-internal")
    for data in (
        ProductCreate(name="Other", owner_id="bob"),
        ProductCreate(name="Other", agent_id="engineer"),
        ProductCreate(name="Other", repository=Repository(url="https://github.com/example/private")),
    ):
        with pytest.raises(CompanyError) as error:
            service.create_product(data=data, **mutation(principal=delegated))
        assert error.value.status == 403
    with pytest.raises(CompanyError):
        service.create_product(
            data=ProductCreate(name="Escaped"), **mutation(principal=replace(delegated, product_id=created["id"]))
        )
    with pytest.raises(CompanyError):
        service.create_product(
            data=ProductCreate(name="Escaped"),
            **mutation(principal=replace(delegated, scopes=("company:read", "company:write"))),
        )


def test_setup_cannot_be_performed_by_an_agent(setup):
    with pytest.raises(CompanyError):
        setup[2].setup_agentos(data=CompanySetup(), **mutation(principal=replace(principal(), agent_id="agent:pm")))


def test_repository_requires_sandbox_before_ready(setup):
    from test_execution import make_work
    from test_progression import accept_ready

    os, _ = runtime_os(setup)
    product, task = make_work(os.company, project=True)
    os.company.update_product(
        product_id=product["id"],
        version=product["version"],
        data=ProductPatch(repository=Repository(url="https://github.com/example/application")),
        **mutation(principal=caller()),
    )
    with pytest.raises(CompanyError, match="sandboxed engineering agent"):
        accept_ready(os.company, task)
    assert os.company.get_task(principal=caller(), task_id=task["id"])["status"] == "backlog"


def engineering_work(setup, monkeypatch):
    pytest.importorskip("agno.sandbox.repository")
    from agno.sandbox.docker import DockerSandbox
    from test_progression import accept_ready

    from agno.agents.codex import CodexAgent
    from agno.os.company import repository
    from agno.os.company.schemas import ProjectCreate, TaskCreate

    os, _ = runtime_os(setup)
    engineer = CodexAgent(id="codex", name="engineering agent", db=os.db, sandbox=DockerSandbox(image="fixture"))
    os.agents.append(engineer)
    service = os.company
    source = {"url": "https://github.com/example/application", "commit": "a" * 40}
    monkeypatch.setattr(repository, "_resolve_commit", lambda *_: dict(source))
    product = service.setup_agentos(
        data=CompanySetup(repository=Repository(url=source["url"]), agent_id=engineer.id),
        **mutation(principal=caller()),
    )
    project = service.create_project(
        product_id=product["id"], data=ProjectCreate(title="Upgrade AgentOS"), **mutation(principal=caller())
    )
    task = service.create_task(
        product_id=product["id"],
        data=TaskCreate(project_id=project["id"], title="Upgrade", instructions="Upgrade and run compatibility tests"),
        **mutation(principal=caller()),
    )
    task = accept_ready(service, task)
    return os, service, product, project, task, source


def test_engineering_pins_source_serializes_product_and_reuses_task_session(setup, monkeypatch):
    from test_progression import accept_ready

    from agno.os.company.schemas import TaskCreate, Transition

    os, service, product, project, task, source = engineering_work(setup, monkeypatch)
    runtime = service._runtime
    assert task["source"] == source
    first = runtime._reserve(caller(), task["id"], task["version"], "first", "", "ready")
    assert first["payload"]["kwargs"]["repository"] == source
    assert runtime._reserve(caller(), task["id"], task["version"], "first", "", "ready")["id"] == first["id"]
    second = service.create_task(
        product_id=product["id"],
        data=TaskCreate(project_id=project["id"], title="Another change", instructions="Test another change"),
        **mutation(principal=caller()),
    )
    second = accept_ready(service, second)
    with pytest.raises(CompanyError, match="Another engineering agent"):
        runtime._reserve(caller(), second["id"], second["version"], "second", "", "ready")
    assert service.get_task(principal=caller(), task_id=second["id"])["status"] == "ready"
    with pytest.raises(CompanyError, match="accepted Tasks"):
        service.update_product(
            product_id=product["id"],
            version=product["version"],
            data=ProductPatch(repository=None),
            **mutation(principal=caller()),
        )
    runtime._settle(first, "completed")
    reviewed = service.get_task(principal=caller(), task_id=task["id"])
    assert reviewed["status"] == "in_review"
    revised = service.transition_task(
        task_id=task["id"],
        version=reviewed["version"],
        data=Transition(to_status="in_progress", reason="Fix the failing compatibility test"),
        **mutation(principal=caller()),
    )
    retry = runtime._reserve(caller(), task["id"], revised["version"], "revision", "Fix the test", "manual")
    assert retry["session_id"] == first["session_id"] and retry["payload"]["kwargs"]["repository"] == source
    runtime._settle(retry, "completed")
    next_run = runtime._reserve(caller(), second["id"], second["version"], "second", "", "ready")
    assert next_run["session_id"] != first["session_id"]


def test_engineering_claim_rejects_tampering_and_revoked_membership(setup, monkeypatch):
    os, service, product, _, task, _ = engineering_work(setup, monkeypatch)
    runtime = service._runtime
    row = runtime._reserve(caller(), task["id"], task["version"], "first", "", "ready")
    monkeypatch.setattr(runtime, "_principal", lambda _: caller())
    job = {
        "id": str(row["id"]),
        "user_id": "alice",
        "component_id": row["agent_id"],
        "session_id": row["session_id"],
        "payload": row["payload"],
        "idempotency_key": "company:" + str(row["id"]),
    }
    assert runtime._claim_context(job).product_id == str(product["id"])
    with pytest.raises(CompanyError, match="Repository source changed"):
        runtime._claim_context({**job, "payload": {"kwargs": {"repository": {"commit": "b" * 40}}}})
    setup[1].set_disabled("alice", True)
    with pytest.raises(CompanyError):
        runtime._claim_context(job)


@pytest.mark.parametrize("sdk", ["codex", "claude"])
def test_docker_ready_review_and_revision_use_real_repository_checkpoint(setup, monkeypatch, tmp_path, sdk):
    """Credential-free runtime: real Docker/Git/queue/checkpoint, no model-generated code."""
    import os as environment

    image = environment.getenv("COMPANY_TEST_SANDBOX_IMAGE")
    if not image:
        pytest.skip("Set COMPANY_TEST_SANDBOX_IMAGE to the combined runtime image")
    pytest.importorskip("agno.sandbox.repository")
    from agno.sandbox.checkpoint import FileCheckpointStore
    from agno.sandbox.docker import DockerSandbox
    from fastapi.testclient import TestClient
    from test_progression import accept_ready, tick

    from agno.agents.codex import CodexAgent
    from agno.os.company.schemas import ProjectCreate, TaskCreate, Transition

    os, _ = runtime_os(setup)
    provider = DockerSandbox(
        image=image,
        namespace="company-engineer-test",
        network="isolated",
        memory_mb=512,
        workspace_mb=64,
        env={"AGNO_SANDBOX_TEST_RUNTIME": "1"},
        checkpoints=FileCheckpointStore(tmp_path / "checkpoints"),
    )
    from agno.agents.claude import ClaudeAgent

    engineer = (CodexAgent if sdk == "codex" else ClaudeAgent)(id=sdk, name=sdk.title(), db=os.db, sandbox=provider)
    # Use the sandbox's explicit fixture protocol, while exercising the real registered adapter path.
    monkeypatch.setattr(engineer, "_sandbox_runtime", "fixture")
    os.agents.append(engineer)
    service = os.company
    handles = []
    create = provider.acreate

    async def remember(*args, **kwargs):
        handle = await create(*args, **kwargs)
        handles.append(handle)
        if len(handles) == 1:
            prepared = await provider.aexec(
                handle,
                [
                    "python",
                    "-c",
                    "from pathlib import Path; p=Path('/workspace/output'); p.mkdir(exist_ok=True); (p/'checks.md').write_text('Credential-free fixture output')",
                ],
            )
            assert prepared.exit_code == 0, prepared.stderr
        return handle

    monkeypatch.setattr(provider, "acreate", remember)
    try:
        with TestClient(os.get_app()) as client:
            product = service.setup_agentos(
                data=CompanySetup(
                    repository=Repository(url="https://github.com/octocat/Hello-World", branch="master"),
                    agent_id=engineer.id,
                ),
                **mutation(principal=caller()),
            )
            project = service.create_project(
                product_id=product["id"], data=ProjectCreate(title="Check repository"), **mutation(principal=caller())
            )
            task = service.create_task(
                product_id=product["id"],
                data=TaskCreate(
                    project_id=project["id"],
                    title="Inspect checkout",
                    instructions="Inspect the repository and report actual checks",
                ),
                **mutation(principal=caller()),
            )
            service.files.write(
                product_id=product["id"],
                path="brief.md",
                content="Pinned product context",
                expected_version=0,
                **mutation(principal=caller()),
            )
            task = accept_ready(service, task)
            tick(client, service)
            # Container startup, checkout and checkpointing may exceed the ordinary model fixture's ten seconds.
            import time

            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                current = service.get_task(principal=caller(), task_id=task["id"])
                if current["status"] == "in_review":
                    break
                time.sleep(0.2)
            assert current["status"] == "in_review", service.list_runs(principal=caller(), task_id=task["id"])
            first = service.list_runs(principal=caller(), task_id=task["id"])["data"][0]
            result = service.get_task_result(principal=caller(), task_id=task["id"], run_id=first["run_id"])
            assert result["source"] == task["source"] and result["status"] == "completed"
            saved = service.files.read(
                principal=caller(),
                product_id=product["id"],
                path=f"tasks/{task['id']}/results/{first['run_id']}/checks.md",
            )
            assert saved["content"] == "Credential-free fixture output"
            service.files.write(
                product_id=product["id"],
                path="brief.md",
                content="New input for later Tasks",
                expected_version=1,
                **mutation(principal=caller()),
            )
            revised = service.transition_task(
                task_id=task["id"],
                version=current["version"],
                data=Transition(to_status="in_progress", reason="Inspect restored checkout"),
                **mutation(principal=caller()),
            )
            second = service.run_task(
                principal=caller(),
                task_id=task["id"],
                version=revised["version"],
                idempotency_key="revision",
                message="Inspect restored files",
            )
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                current = service.get_task(principal=caller(), task_id=task["id"])
                if current["status"] == "in_review":
                    break
                time.sleep(0.2)
            assert current["status"] == "in_review", service.list_runs(principal=caller(), task_id=task["id"])
            assert second["session_id"] == first["session_id"]
            assert len(handles) == 2 and handles[0].provider_ref != handles[1].provider_ref
            import json
            import subprocess

            from agno.sandbox._harness import coordinator
            from agno.sandbox.checkpoint import CheckpointRef
            from sqlalchemy import select

            runner = coordinator(engineer)

            async def restore():
                record = await runner.store._transaction(
                    lambda connection: connection.execute(select(runner.store.bindings.c.record)).scalar_one()
                )
                await runner.transfer.store.arestore(CheckpointRef(**record["checkpoint"]), tmp_path / "restored")

            client.portal.call(restore)
            restored = tmp_path / "restored"
            actual = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=restored / "workspace/repository", text=True
            ).strip()
            assert actual == task["source"]["commit"]
            assert (restored / "workspace/context/product/brief.md").read_text() == "Pinned product context"
            assert (restored / "workspace/output/checks.md").read_text() == "Credential-free fixture output"
            assert json.loads((restored / "native/repository.json").read_text()) == task["source"]
            assert (restored / "workspace/fixture-effects.txt").read_text().splitlines() == [
                first["run_id"],
                second["run_id"],
            ]
            tick(client, service)
            assert service.get_task(principal=caller(), task_id=task["id"])["status"] == "in_review"
    finally:
        for handle in handles:
            asyncio.run(provider.adestroy(handle))


def test_setup_key_cannot_replay_an_ordinary_product_creation(setup):
    service = setup[2]
    args = mutation()
    ordinary = service.create_product(data=ProductCreate(name="AgentOS"), **args)
    builtin = service.setup_agentos(data=CompanySetup(), **args)
    assert builtin["id"] != ordinary["id"] and builtin["builtin"] == "agentos"
