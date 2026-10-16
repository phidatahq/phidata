"""Heartbeat routes consume scheduler behavior and preserve bounded authority."""

import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.company import Product
from agno.company.manager import CompanyManager
from agno.company.routines import _RoutineAuthorization, load_routine_skills
from agno.db.schemas.scheduler import Schedule
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, CompanyConfig
from agno.os.authz.run_context import restore_authorization
from agno.run.authorization import AUTHORIZATION_HEADER, authorization_scope
from agno.scheduler.executor import ScheduleExecutor


@pytest.fixture
def system(tmp_path):
    db = SqliteDb(db_file=str(tmp_path / "company.db"))
    agent = Agent(id="reader", telemetry=False)
    os = AgentOS(db=db, agents=[agent], company=CompanyConfig(), telemetry=False)
    with TestClient(os.get_app()) as client:
        yield client, os, db
    db.close()


def test_routine_scheduler_wrappers(system):
    client, os, db = system
    product = client.post("/company/products", json={"name": "Docs"}).json()
    body = dict(
        product_id=product["id"],
        name="intake",
        template="intake",
        executor_type="agent",
        executor_id="reader",
        cron_expr="0 * * * *",
    )
    response = client.post("/company/routines", json=body)
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["managed_by"] == "company"
    assert row["target_id"] == "reader"
    assert row["payload"]["metadata"] == {"product_id": product["id"], "template": "intake", "auto_accept": False}
    assert row["payload"]["message"].endswith(load_routine_skills().get_skill("intake").instructions)
    assert db.get_product(product["id"])["metadata"]["routine_ids"] == [row["id"]]
    path = "/company/routines/" + row["id"]
    assert client.post(path + "/pause").json()["enabled"] is False
    assert client.post(path + "/resume").json()["enabled"] is True
    assert client.patch(path, json={"instructions": "Check quietly"}).status_code == 200
    message = db.get_schedule(row["id"])["payload"]["message"]
    assert product["id"] in message and message.endswith("Check quietly")
    assert client.patch(path, json={"auto_accept": True}).status_code == 422
    assert client.get(path + "/runs").json()["meta"]["total_count"] == 0
    assert len(client.get("/company/routines").json()["data"]) == 1


@pytest.mark.parametrize("field,value", [("cron_expr", "bad cron"), ("timezone", "not/a/timezone")])
def test_invalid_setup_does_not_create_records(system, field, value):
    client, _, db = system
    routine = dict(name="intake", template="intake", executor_type="agent", executor_id="reader", cron_expr="0 * * * *")
    routine[field] = value
    response = client.post("/company/setup", json={"name": "Invalid", "routines": [routine]})
    assert response.status_code == 422
    assert db.get_products()[1] == 0


@pytest.mark.asyncio
async def test_summary_uses_telegram_interface_transport(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from agno.company.summary import adeliver_summary

    bot = SimpleNamespace(send_message=AsyncMock(), close_session=AsyncMock())
    factory = Mock(return_value=bot)
    monkeypatch.setattr("telebot.async_telebot.AsyncTeleBot", factory)
    interface = SimpleNamespace(type="telegram", token="configured-token")
    await adeliver_summary([interface], "telegram", "123", "Product report")
    factory.assert_called_once_with("configured-token")
    assert bot.send_message.await_args.args[:2] == (123, "Product report")
    bot.close_session.assert_awaited_once()


def test_sources_setup_restart_and_diagnostics(system, tmp_path, monkeypatch):
    client, os, db = system
    path = tmp_path / "readme.md"
    path.write_text("# Release\nNew capability.\n")
    body = {
        "name": "AgentOS",
        "sources": [{"type": "markdown", "reference": str(path), "credential_ref": "HEARTBEAT_TOKEN"}],
    }
    first = client.post("/company/setup", json=body)
    assert first.status_code == 201, first.text
    assert client.patch("/company/products/" + first.json()["id"], json={"name": "Human edit"}).status_code == 200
    client.post("/company/products", json={"name": "Later Product"}).raise_for_status()
    second = client.post("/company/setup", json=body)
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["name"] == "Human edit"
    sources = client.get("/company/sources").json()["data"]
    assert len(sources) == 1
    manager = CompanyManager(db)
    monkeypatch.setenv("HEARTBEAT_TOKEN", "never-forward-this-value")
    evidence = manager.read_source(sources[0]["id"], "run-1")
    assert "never-forward-this-value" not in json.dumps(evidence)
    from agno.os.diagnostics import run_diagnostics

    assert next(c for c in run_diagnostics(os).checks if c.name == "env:HEARTBEAT_TOKEN").status == "PASS"
    monkeypatch.delenv("HEARTBEAT_TOKEN")
    assert next(c for c in run_diagnostics(os).checks if c.name == "env:HEARTBEAT_TOKEN").status == "FAIL"
    assert client.delete("/company/sources/" + sources[0]["id"]).status_code == 204
    assert client.get("/company/sources").json()["data"] == []
    assert client.post("/company/sources/" + sources[0]["id"] + "/restore").status_code == 200


@pytest.mark.asyncio
async def test_company_metadata_survives_executor_scrub(monkeypatch):
    executor = ScheduleExecutor(base_url="http://test", internal_service_token="test")
    captured = {}

    async def capture(client, url, headers, payload, resource_type, resource_id, timeout_seconds):
        captured.update(payload=payload, headers=headers)
        return {"status": "success"}

    monkeypatch.setattr(executor, "_get_client", AsyncMock())
    monkeypatch.setattr(executor, "_background_run", capture)
    metadata = {"product_id": "p", "template": "intake", "auto_accept": False, "agno_component_version": 99}
    schedule = Schedule(
        id="s",
        name="test",
        cron_expr="0 * * * *",
        endpoint="/agents/reader/runs",
        managed_by="company",
        payload={"message": "Check", "metadata": metadata},
    )
    await executor._call_endpoint(schedule)
    assert json.loads(captured["payload"]["metadata"]) == {
        k: v for k, v in metadata.items() if k != "agno_component_version"
    }
    authority = restore_authorization(None, json.loads(captured["headers"][AUTHORIZATION_HEADER]))
    assert isinstance(authority, _RoutineAuthorization)
    with pytest.raises(PermissionError, match="schedules"):
        authority.require("schedules", "write")
    with pytest.raises(PermissionError, match="schedules"):
        await authority.arequire("schedules", "write")


def test_routine_cannot_accept(system):
    _, _, db = system
    manager = CompanyManager(db)
    product = manager.create("Docs")
    task = manager.create_task(product["id"], "Draft")
    with authorization_scope(lambda: _RoutineAuthorization(None)):
        with pytest.raises(PermissionError, match="cannot accept"):
            manager.transition_task(task["id"], "ready", "self approval", executor_type="agent", executor_id="reader")
    assert manager.get_task(task["id"])["status"] == "backlog"


def test_yaml_and_code_rehydrate_without_reset(tmp_path):
    db = SqliteDb(db_file=str(tmp_path / "declare.db"))
    declaration = Product(name="SDK", purpose="Maintain SDK")
    os = AgentOS(db=db, company=CompanyConfig(products=[declaration]), telemetry=False)
    with TestClient(os.get_app()) as client:
        first = client.get("/company/products").json()["data"][0]
        client.patch("/company/products/" + first["id"], json={"purpose": "Human direction"})
    with TestClient(AgentOS(db=db, company=CompanyConfig(products=[declaration]), telemetry=False).get_app()) as client:
        rows = client.get("/company/products").json()["data"]
        assert len(rows) == 1
        assert rows[0]["purpose"] == "Human direction"
    config = tmp_path / "config.yaml"
    config.write_text("company:\n  products:\n    - name: SDK\n      purpose: stale declaration\n")
    with TestClient(AgentOS(db=db, config=str(config), telemetry=False).get_app()) as client:
        assert client.get("/company/products").json()["data"][0]["purpose"] == "Human direction"
    db.close()


@pytest.mark.parametrize("isolation", [False, True])
def test_sources_and_routines_scopes_and_ownership(tmp_path, isolation):
    from datetime import datetime, timedelta, timezone

    import jwt

    from agno.os.config import AuthorizationConfig

    secret = "heartbeat-isolation-secret"
    scopes = [
        "products:read",
        "products:write",
        "sources:read",
        "sources:write",
        "sources:delete",
        "routines:read",
        "routines:write",
        "schedules:read",
        "schedules:write",
        "agents:reader:run",
    ]

    def headers(user, granted=None):
        return {
            "Authorization": "Bearer "
            + jwt.encode(
                {
                    "sub": user,
                    "private_claim": "private-claim-" + user,
                    "aud": "heartbeat",
                    "scopes": scopes if granted is None else granted,
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                },
                secret,
                algorithm="HS256",
            )
        }

    db = SqliteDb(db_file=str(tmp_path / "isolated.db"))
    os = AgentOS(
        id="heartbeat",
        db=db,
        agents=[Agent(id="reader", telemetry=False)],
        company=CompanyConfig(),
        telemetry=False,
        authorization=True,
        authorization_config=AuthorizationConfig(
            verification_keys=[secret], algorithm="HS256", user_isolation=isolation
        ),
    )
    with TestClient(os.get_app()) as client:
        product = client.post("/company/products", headers=headers("alice"), json={"name": "Docs"}).json()
        body = {"product_id": product["id"], "type": "markdown", "reference": "/docs"}
        assert client.post("/company/sources", headers=headers("bob"), json=body).status_code == (
            403 if isolation else 201
        )
        assert client.post("/company/sources", headers=headers("alice"), json=body).status_code == 201
        assert client.get("/company/sources", headers=headers("bob", ["sources:read"])).json()["data"]
        routine = {
            "product_id": product["id"],
            "name": "intake",
            "template": "intake",
            "executor_type": "agent",
            "executor_id": "reader",
            "cron_expr": "0 * * * *",
        }
        assert (
            client.post(
                "/company/routines",
                headers=headers("alice", [s for s in scopes if s != "schedules:write"]),
                json=routine,
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/company/routines",
                headers=headers("alice", [s for s in scopes if s != "agents:reader:run"]),
                json=routine,
            ).status_code
            == 403
        )
        created = client.post("/company/routines", headers=headers("alice"), json=routine)
        assert created.status_code == 201
        routine_id = created.json()["id"]
        assert routine_id in {
            row["id"] for row in client.get("/company/routines", headers=headers("bob")).json()["data"]
        }
        path = "/company/routines/" + routine_id
        assert client.get(path + "/runs", headers=headers("bob")).status_code == 200
        if isolation:
            assert client.patch(path, headers=headers("bob"), json={"instructions": "Change"}).status_code == 403
            assert client.post(path + "/pause", headers=headers("bob")).status_code == 403
            assert client.post(path + "/resume", headers=headers("bob")).status_code == 403
        assert "private-claim-alice" in json.dumps(db.get_schedule(routine_id)["payload"])
        actor = "alice" if isolation else "bob"
        for action, enabled in (("pause", False), ("resume", True)):
            response = client.post(path + "/" + action, headers=headers(actor))
            assert response.status_code == 200, response.text
            assert response.json()["enabled"] is enabled
            assert "payload" not in response.json()
            assert "_agno_authorization" not in response.text
            assert "private-claim-alice" not in response.text
        assert "private-claim-alice" in json.dumps(db.get_schedule(routine_id)["payload"])
        assert client.post("/company/setup", headers=headers("bob"), json={"name": "Other setup"}).status_code == 409
    db.close()


@pytest.mark.parametrize("failure", ["create_schedule", "add_product_routine"])
def test_setup_retry_repairs_partial_records_and_retains_edits(system, tmp_path, monkeypatch, failure):
    client, os, db = system
    body = dict(
        name="Setup",
        sources=[dict(type="markdown", reference=str(tmp_path / "readme.md"))],
        routines=[
            dict(name="refresh", template="refresh", executor_type="agent", executor_id="reader", cron_expr="0 * * * *")
        ],
    )
    original = getattr(db, failure)

    def unavailable(*args, **kwargs):
        raise RuntimeError("Injected storage failure")

    monkeypatch.setattr(db, failure, unavailable)
    with pytest.raises(RuntimeError, match="Injected storage failure"):
        client.post("/company/setup", json=body)
    monkeypatch.setattr(db, failure, original)
    manager = CompanyManager(db)
    manager.update("company-setup", name="Human edit")
    source = manager.list_sources()[0][0]
    manager.delete_source(source["id"])
    schedules = db.get_schedules()[0]
    if schedules:
        db.update_schedule(
            schedules[0]["id"], enabled=False, payload={**schedules[0]["payload"], "message": "Human instructions"}
        )
    retry = client.post("/company/setup", json=body)
    assert retry.status_code == 200, retry.text
    assert retry.json()["name"] == "Human edit"
    schedules = db.get_schedules()[0]
    assert len(schedules) == 1
    assert retry.json()["metadata"]["routine_ids"] == [schedules[0]["id"]]
    assert manager.list_sources()[1] == 0
    if failure == "add_product_routine":
        assert schedules[0]["enabled"] is False
        assert schedules[0]["payload"]["message"] == "Human instructions"
    client.post("/company/setup", json=body).raise_for_status()
    assert len(db.get_schedules()[0]) == 1
    manager.delete("company-setup")
    assert client.post("/company/setup", json=body).json()["deleted_at"] is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("async_tools", [False, True])
async def test_source_tools_only_require_source_and_proposal_scopes(tmp_path, async_tools):
    from agno.os.auth import _default_authorization_provider
    from agno.os.authz.provider import AuthorizationContext
    from agno.run import RunContext
    from agno.run.authorization import RunAuthorization
    from agno.tools.company import CompanyTools

    db = SqliteDb(db_file=str(tmp_path / "permissions.db"))
    manager = CompanyManager(db)
    product = manager.create("Docs")
    path = tmp_path / "page.md"
    path.write_text("Document the released API")
    source = manager.create_source(product["id"], "markdown", str(path))
    tools = CompanyTools(db)
    authority = RunAuthorization(
        _default_authorization_provider(),
        AuthorizationContext(principal_id="reader", scopes=["sources:read", "tasks:write"]),
    )
    context = RunContext(run_id="source-run", session_id="session", user_id="reader")
    args = dict(
        source_id=source["id"],
        title="Document API",
        brief="Write API guide",
        proposal_key="api-guide",
        evidence_links=[path.as_uri()],
        _agno_run_context=context,
    )
    with authorization_scope(lambda: _RoutineAuthorization(authority, "routine")):
        if async_tools:
            evidence = [
                json.loads(await tools.aread_company_source(source["id"], path=path.name, _agno_run_context=context))
            ]
            args["evidence_hashes"] = {item["link"]: item["content_hash"] for item in evidence}
            task = json.loads(await tools.aintake_company_source(**args))
        else:
            evidence = [json.loads(tools.read_company_source(source["id"], path=path.name, _agno_run_context=context))]
            args["evidence_hashes"] = {item["link"]: item["content_hash"] for item in evidence}
            task = json.loads(tools.intake_company_source(**args))
    assert evidence[0]["content_hash"] == task["evidence"][0]["content_hash"]
    assert task["status"] == "backlog"
    authority.context.scopes = ["tasks:write"]
    with authorization_scope(lambda: authority):
        with pytest.raises(PermissionError):
            tools.read_company_source(source["id"], _agno_run_context=context)
    db.close()


def test_company_yaml_rejects_unknown_keys():
    from pydantic import ValidationError

    from agno.os.config import AgentOSConfig

    with pytest.raises(ValidationError):
        AgentOSConfig(company={"produts": []})


@pytest.mark.parametrize("template", ["refresh", "intake", "summary"])
def test_each_routine_template_targets_the_product_in_its_message(system, template):
    client, _, _ = system
    product = client.post("/company/products", json={"name": "Target"}).json()
    row = client.post(
        "/company/routines",
        json=dict(
            product_id=product["id"],
            name=template,
            template=template,
            executor_type="agent",
            executor_id="reader",
            cron_expr="0 * * * *",
        ),
    ).json()
    assert row["payload"]["metadata"]["product_id"] == product["id"]
    assert product["id"] in row["payload"]["message"]
    instructions = load_routine_skills().get_skill(template).instructions
    assert "Product identified in the message" in instructions
    assert "product_id in run metadata" not in instructions


def test_custom_company_tools_resolve_os_interfaces_and_human_origin(tmp_path, monkeypatch):
    from fastapi import APIRouter

    from agno.models.openai import OpenAIResponses
    from agno.os.interfaces.base import BaseInterface
    from agno.run import RunContext
    from agno.tools.company import CompanyTools

    class Interface(BaseInterface):
        type = "slack"

        def get_router(self, **kwargs):
            return APIRouter()

    db = SqliteDb(db_file=str(tmp_path / "summary.db"))
    interface = Interface()
    toolkit = CompanyTools(db)
    executor = Agent(id="custom", tools=[toolkit], telemetry=False)
    os = AgentOS(
        db=db,
        agents=[executor],
        interfaces=[interface],
        company=CompanyConfig(model=OpenAIResponses(id="offline")),
        telemetry=False,
    )
    assert toolkit.interfaces is os.interfaces
    assert "summarize_company_product" not in os.product_manager.tools[0].functions
    delivery = AsyncMock()
    monkeypatch.setattr("agno.company.summary.adeliver_summary", delivery)
    with TestClient(os.get_app()) as client:
        product = client.post(
            "/company/products",
            json={"name": "Summary", "metadata": {"summary": {"interface": "slack", "destination": "configured"}}},
        ).json()
        task = client.post("/company/tasks", json={"product_id": product["id"], "title": "Human work"}).json()
        assert task["origin"] == "human" and task["routine_id"] is None and task["dedupe_key"] is None
        context = RunContext(run_id="report", session_id="session", user_id="alice")
        proposed = json.loads(toolkit.propose_company_task(product["id"], "Proposed work", _agno_run_context=context))
        assert proposed["origin"] == "product_manager"
        result = json.loads(
            toolkit.summarize_company_product(
                product["id"], narrative="Two items need review.", _agno_run_context=context
            )
        )
        assert result["delivered"] is True
        page = CompanyManager(db).read_wiki(product["id"], "summary.md").content
        assert "Two items need review." in page and "## What changed" in page
        assert "Two items need review." in delivery.await_args.args[3]
        assert "Company summary snapshot" not in delivery.await_args.args[3]
    db.close()


@pytest.mark.parametrize("name", ["weekday/refresh", "x" * 240])
def test_routine_composed_name_validation_returns_422(system, name):
    client, _, db = system
    product = client.post("/company/products", json={"name": "Docs"}).json()
    body = dict(
        product_id=product["id"],
        name=name,
        template="refresh",
        executor_type="agent",
        executor_id="reader",
        cron_expr="0 * * * *",
    )
    response = client.post("/company/routines", json=body)
    assert response.status_code == 422, response.text
    assert "name" in response.json()["detail"]
    assert not (db.get_product(product["id"]).get("metadata") or {}).get("routine_ids")
    body["name"] = "x" * (255 - len(product["id"]) - 1)
    created = client.post("/company/routines", json=body)
    assert created.status_code == 201, created.text
    assert len(created.json()["name"]) == 255
    assert client.patch("/company/routines/" + created.json()["id"], json={"cron_expr": "x" * 129}).status_code == 422


@pytest.mark.parametrize("name", ["weekday/refresh", "x" * 250])
def test_setup_invalid_composed_name_has_no_partial_writes(system, name):
    client, _, db = system
    response = client.post(
        "/company/setup",
        json={
            "name": "Docs",
            "routines": [
                dict(name=name, template="refresh", executor_type="agent", executor_id="reader", cron_expr="0 * * * *")
            ],
        },
    )
    assert response.status_code == 422, response.text
    assert db.get_products()[1] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("async_tools", [False, True])
@pytest.mark.parametrize("routine_id", [None, "routine"])
async def test_routine_cannot_use_plain_task_proposals(tmp_path, async_tools, routine_id):
    from agno.run import RunContext
    from agno.tools.company import CompanyTools

    db = SqliteDb(db_file=str(tmp_path / "routine-proposals.db"))
    manager = CompanyManager(db)
    product = manager.create("Docs")
    tools = CompanyTools(db)
    context = RunContext(run_id="run", session_id="session", authorization=_RoutineAuthorization(None, routine_id))
    for _ in range(3):
        with pytest.raises(PermissionError, match="intake_company_source"):
            if async_tools:
                await tools.apropose_company_task(product["id"], "Repeated", _agno_run_context=context)
            else:
                tools.propose_company_task(product["id"], "Repeated", _agno_run_context=context)
    assert manager.list_tasks()[1] == 0
    context.authorization = None
    if async_tools:
        result = await tools.apropose_company_task(product["id"], "Human-directed", _agno_run_context=context)
    else:
        result = tools.propose_company_task(product["id"], "Human-directed", _agno_run_context=context)
    assert json.loads(result)["origin"] == "product_manager"
    db.close()


def test_bounded_source_reader_preserves_configured_boundaries(tmp_path):
    from agno.company.sources import browse_source, read_source

    root = tmp_path / "repo"
    root.mkdir()
    (root / "allowed.md").write_text("Allowed")
    (root / "other.md").write_text("Not configured")
    (root / ".env").write_text("SECRET")
    outside = tmp_path / "outside.md"
    outside.write_text("Outside")
    (root / "escape.md").symlink_to(outside)
    source = dict(id="s", type="git", reference=str(root), config={"paths": ["allowed.md"]})
    assert browse_source(source, "run")["data"] == [{"path": "allowed.md", "link": (root / "allowed.md").as_uri()}]
    for path in ("other.md", ".env", "../outside.md", "escape.md"):
        with pytest.raises(ValueError):
            browse_source(source, "run", path=path)
        with pytest.raises(ValueError):
            read_source(source, "run", links=[(root / path).as_uri()])
    for options in ({"offset": -1}, {"limit": 0}, {"limit": 101}, {"max_chars": 16001}, {"content_offset": -1}):
        with pytest.raises(ValueError):
            browse_source(source, "run", **options)
    assert browse_source(source, "run", offset=99)["next_offset"] is None
    with pytest.raises(ValueError, match="beyond the document"):
        browse_source(source, "run", path="allowed.md", content_offset=100)


def test_website_source_is_bounded_and_cannot_select_another_url(monkeypatch):
    from agno.company.sources import browse_source, read_source
    from agno.knowledge.document import Document
    from agno.utils.string import hash_string_sha256

    content = "Observed website content " * 3000
    calls = []

    def reader(self, url):
        calls.append(url)
        return [Document(content=content)]

    monkeypatch.setattr("agno.knowledge.reader.website_reader.WebsiteReader.read", reader)
    source = dict(id="s", type="website", reference="https://docs.example.test/page", config={})
    page = browse_source(source, "run")
    assert not calls and page["data"][0]["path"] == source["reference"]
    fragment = browse_source(source, "run", path=source["reference"])
    assert len(fragment["content"]) == 8000 and fragment["next_content_offset"] == 8000
    assert fragment["content_hash"] == hash_string_sha256(content)
    with pytest.raises(ValueError):
        browse_source(source, "run", path="https://unconfigured.test")
    with pytest.raises(ValueError):
        read_source(source, "run", links=["https://unconfigured.test"])
    assert calls == [source["reference"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_tools", [False, True])
async def test_refresh_requires_routine_and_saved_delete_authority(tmp_path, async_tools):
    import asyncio

    from agno.os.auth import _default_authorization_provider
    from agno.os.authz.provider import AuthorizationContext
    from agno.run import RunContext
    from agno.run.authorization import RunAuthorization
    from agno.tools.company import CompanyTools

    db = SqliteDb(db_file=str(tmp_path / "refresh.db"))
    manager = CompanyManager(db)
    product = manager.create("Docs", user_id="owner")
    tools = CompanyTools(db, user_isolation=True)
    context = RunContext(run_id="refresh", session_id="session", user_id="owner")

    async def invoke():
        if async_tools:
            return await tools.arefresh_company_product(product["id"], _agno_run_context=context)
        return await asyncio.to_thread(tools.refresh_company_product, product["id"], _agno_run_context=context)

    with pytest.raises(PermissionError, match="Routine authority"):
        await invoke()
    scopes = ["products:read", "projects:read", "tasks:read", "wiki:read", "wiki:write"]
    authority = RunAuthorization(
        _default_authorization_provider(), AuthorizationContext(principal_id="owner", scopes=scopes)
    )
    with authorization_scope(lambda: _RoutineAuthorization(authority, "refresh")):
        with pytest.raises(PermissionError, match="projects:delete"):
            await invoke()
    authority = RunAuthorization(
        _default_authorization_provider(),
        AuthorizationContext(principal_id="owner", scopes=[*scopes, "projects:delete", "tasks:delete"]),
    )
    with authorization_scope(lambda: _RoutineAuthorization(authority, "refresh")):
        assert json.loads(await invoke())["completion_proposals"] == []
    db.close()


@pytest.mark.parametrize("failure", ["link", "enable"])
@pytest.mark.parametrize("pause_pending", [False, True])
def test_routine_create_recovers_disabled_pending_schedule(system, monkeypatch, failure, pause_pending):
    client, _, db = system
    product = client.post("/company/products", json={"name": "Docs"}).json()
    body = dict(
        product_id=product["id"],
        name="refresh",
        template="refresh",
        executor_type="agent",
        executor_id="reader",
        cron_expr="0 * * * *",
    )
    method = "add_product_routine" if failure == "link" else "update_schedule"
    original = getattr(db, method)

    def fail(*args, **kwargs):
        raise RuntimeError("Interrupted creation")

    monkeypatch.setattr(db, method, fail)
    with pytest.raises(RuntimeError, match="Interrupted creation"):
        client.post("/company/routines", json=body)
    rows, total = db.get_schedules()
    assert total == 1
    pending = rows[0]
    assert pending["enabled"] is False and pending["next_run_at"] is None
    assert pending["payload"]["_agno_pending_creation"] is True
    assert db.get_schedules(enabled=True)[1] == 0
    monkeypatch.setattr(db, method, original)
    # A changed request must not repurpose an interrupted creation.
    assert client.post("/company/routines", json={**body, "cron_expr": "30 * * * *"}).status_code == 409
    if pause_pending:
        assert client.post("/company/routines/" + pending["id"] + "/pause").status_code == 200
        assert client.post("/company/routines", json=body).status_code == 409
        assert db.get_schedule(pending["id"])["enabled"] is False
        assert client.post("/company/routines/" + pending["id"] + "/resume").status_code == 200
        assert db.get_product(product["id"])["metadata"]["routine_ids"] == [pending["id"]]
        return
    result = client.post("/company/routines", json=body)
    assert result.status_code == 201, result.text
    assert result.json()["id"] == pending["id"] and result.json()["enabled"] is True
    assert "_agno_pending_creation" not in result.json()["payload"]
    assert db.get_product(product["id"])["metadata"]["routine_ids"] == [pending["id"]]
    assert db.get_schedules()[1] == 1
    # A later duplicate POST must not reactivate a deliberate pause.
    assert client.post("/company/routines/" + pending["id"] + "/pause").status_code == 200
    assert client.post("/company/routines", json=body).status_code == 409
    assert db.get_schedule(pending["id"])["enabled"] is False


@pytest.mark.parametrize("isolation", [False, True])
def test_pending_routine_creation_cannot_be_recovered_by_another_creator(tmp_path, monkeypatch, isolation):
    from datetime import datetime, timedelta, timezone

    import jwt

    from agno.os.config import AuthorizationConfig

    secret = "pending-routine-test-secret"
    db = SqliteDb(db_file=str(tmp_path / "pending.db"))
    os = AgentOS(
        id="pending-routines",
        db=db,
        agents=[Agent(id="reader", telemetry=False)],
        company=CompanyConfig(),
        telemetry=False,
        authorization=True,
        authorization_config=AuthorizationConfig(
            verification_keys=[secret], algorithm="HS256", user_isolation=isolation
        ),
    )

    def headers(user):
        return {
            "Authorization": "Bearer "
            + jwt.encode(
                {
                    "sub": user,
                    "aud": "pending-routines",
                    "scopes": ["products:write", "routines:write", "schedules:write", "agents:reader:run"],
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                },
                secret,
                algorithm="HS256",
            )
        }

    original = db.add_product_routine

    def fail(*args, **kwargs):
        raise RuntimeError("Link interrupted")

    with TestClient(os.get_app()) as client:
        product = client.post("/company/products", json={"name": "Docs"}, headers=headers("alice")).json()
        body = dict(
            product_id=product["id"],
            name="refresh",
            template="refresh",
            executor_type="agent",
            executor_id="reader",
            cron_expr="0 * * * *",
        )
        monkeypatch.setattr(db, "add_product_routine", fail)
        with pytest.raises(RuntimeError, match="Link interrupted"):
            client.post("/company/routines", json=body, headers=headers("alice"))
        pending = db.get_schedules()[0][0]
        assert pending["user_id"] == "alice"
        monkeypatch.setattr(db, "add_product_routine", original)
        bob = client.post("/company/routines", json=body, headers=headers("bob"))
        if isolation:
            assert bob.status_code == 403
        else:
            # Scheduler names are per creator: Bob can create his own, but cannot recover Alice's.
            assert bob.status_code == 201, bob.text
            assert bob.json()["id"] != pending["id"]
        assert db.get_schedule(pending["id"])["enabled"] is False
        alice = client.post("/company/routines", json=body, headers=headers("alice"))
        assert alice.status_code == 201, alice.text
        assert alice.json()["id"] == pending["id"] and alice.json()["enabled"] is True
    db.close()
