"""Company playbook, bounded tools and framework Product Manager contracts."""

import inspect
import json

import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.company import CompanyManager
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, CompanyConfig, OSManager
from agno.registry import Registry
from agno.registry._reserved import PRODUCT_MANAGER_ID
from agno.run import RunContext
from agno.tools.company import CompanyTools


@pytest.mark.parametrize("manager", [False, True])
def test_product_manager_assembly_and_model_precedence(tmp_path, manager):
    db = SqliteDb(db_file=str(tmp_path / "os.db"))
    first, override = OpenAIResponses(id="first"), OpenAIResponses(id="override")
    registry = Registry(models=[first])
    os = AgentOS(
        db=db,
        registry=registry,
        company=CompanyConfig(model=override),
        manager=OSManager(access_docs=False) if manager else None,
        telemetry=False,
    )
    pm = os.product_manager
    assert pm.id == PRODUCT_MANAGER_ID and pm.model is override
    assert pm.learning.decision_log.db is db
    assert pm not in registry.agents and not registry.tools
    assert (pm in os.manager.members) if manager else (pm in os._agents)
    assert (pm not in os._agents) if manager else True
    os.resync(os.get_app())
    assert pm not in registry.agents and not registry.tools
    tools = pm.tools[0]
    assert {"create_company_product", "create_company_routine"} <= tools.functions.keys()
    assert tools.registry is registry
    assert not any("schedule" in name or "transition" in name for name in tools.functions)
    assert "log_company_decision" not in tools.functions
    assert "summarize_company_product" not in tools.functions
    assert "refresh_company_product" not in tools.functions
    assert "summarize_company_product" in CompanyTools(db, summary_tools=True).functions
    assert {fn.__name__ for fn in pm.learning.decision_log.get_tools()} == {
        "log_company_decision",
        "search_company_decisions",
    }
    inherited = AgentOS(db=db, registry=Registry(models=[first, override]), company=CompanyConfig(), telemetry=False)
    assert inherited.product_manager.model is first


def test_company_tools_published_only_over_mcp_are_bound(tmp_path):
    from agno.os import MCPConfig

    db = SqliteDb(db_file=str(tmp_path / "mcp.db"))
    registry = Registry(agents=[Agent(id="reader")])
    exposed, explicit = CompanyTools(db), CompanyTools(db, registry=Registry())
    AgentOS(
        db=db,
        registry=registry,
        company=CompanyConfig(automation_history_retention_days=7),
        mcp=MCPConfig(tools=[exposed, explicit]),
        telemetry=False,
    )
    assert exposed.registry is registry and exposed._schedule_db is db
    assert exposed._automation_history_retention_days == 7
    assert explicit.registry is not registry


def test_no_model_manual_api_and_disabled_company(tmp_path, caplog):
    db = SqliteDb(db_file=str(tmp_path / "no-model.db"))
    os = AgentOS(db=db, company=CompanyConfig(), telemetry=False)
    assert not any("Product Manager unavailable" in record.message for record in caplog.records)
    assert os.product_manager is None and "CompanyConfig(model=" in os.product_manager_unavailable_reason
    assert any(c.name == "company" and c.status == "WARN" for c in os.run_diagnostics().checks)
    assert TestClient(os.get_app()).post("/company/decisions", json={"decision": "manual"}).status_code == 201
    disabled = AgentOS(db=db, telemetry=False)
    assert not any(getattr(route, "path", "").startswith("/company") for route in disabled.get_app().routes)
    with pytest.raises(ValueError, match="reserved"):
        AgentOS(db=db, agents=[Agent(id=PRODUCT_MANAGER_ID)], telemetry=False)
    with pytest.raises(ValueError, match="reserved"):
        Registry(agents=[Agent(id=PRODUCT_MANAGER_ID)])


@pytest.mark.asyncio
@pytest.mark.parametrize("use_async", [False, True])
async def test_tools_identity_fence_and_learning(tmp_path, use_async):
    db = SqliteDb(db_file=str(tmp_path / "tools.db"))
    from agno.agent import Agent

    manager = CompanyManager(db, registry=Registry(agents=[Agent(id="writer")]))
    product = manager.create(name="SDK", user_id="alice")
    project = manager.create_project(product_id=product["id"], name="Release", user_id="alice")
    tools = CompanyTools(db, user_isolation=True)
    alice = RunContext(run_id="r", session_id="s", user_id="alice")
    bob = RunContext(run_id="r2", session_id="s2", user_id="bob")

    async def invoke(name, *args, **kwargs):
        fn = getattr(tools, ("a" if use_async else "") + name)
        return await fn(*args, **kwargs) if use_async else fn(*args, **kwargs)

    task = json.loads(
        await invoke("propose_company_task", product["id"], "Draft", project_id=project["id"], _agno_run_context=alice)
    )
    assert task["status"] == "backlog" and task["user_id"] == "alice"
    assert json.loads(await invoke("list_company_tasks", _agno_run_context=bob))["meta"]["total_count"] == 1
    with pytest.raises(PermissionError):
        await invoke("edit_company_task", task["id"], "stolen", "no", _agno_run_context=bob)
    await invoke("edit_company_task", task["id"], "Draft", "better", _agno_run_context=alice)
    manager.transition_task(
        task_id=task["id"],
        target="ready",
        reason="approved",
        executor_type="agent",
        executor_id="writer",
        accepted_by="alice",
    )
    with pytest.raises(ValueError, match="Backlog"):
        await invoke("edit_company_task", task["id"], "changed", "no", _agno_run_context=alice)
    await invoke("update_company_status", product["id"], "draft ready", 1, _agno_run_context=alice)
    entry = json.loads(
        await invoke("log_company_decision", "Draft first", reasoning="review needed", _agno_run_context=alice)
    )
    assert entry["user_id"] == "alice" and entry["session_id"] == "s"
    assert entry["agent_id"] is None
    assert manager.list_decisions(agent_id=PRODUCT_MANAGER_ID, session_id="s")[1] == 0
    for function in tools.get_async_functions().values():
        function.process_entrypoint()
        properties = function.parameters.get("properties", {})
        if function.name == "log_company_decision":
            assert "agent_id" not in properties
        assert not {"user_id", "_agno_run_context", "owner", "auto_accept", "accepted_by"} & set(properties)
        if function.name != "create_company_product":
            assert "sources" not in properties
    with pytest.raises(PermissionError):
        await invoke("propose_company_task", product["id"], "anonymous", project_id=project["id"])


@pytest.mark.asyncio
async def test_direct_mcp_has_only_bounded_tools(tmp_path):
    from fastmcp import Client

    from agno.os import MCPConfig
    from agno.os.mcp import build_mcp_server

    db = SqliteDb(db_file=str(tmp_path / "mcp.db"))
    product = CompanyManager(db).create(name="SDK")
    project = CompanyManager(db).create_project(product_id=product["id"], name="Release")
    tools = CompanyTools(db)
    os = AgentOS(db=db, company=CompanyConfig(), mcp=MCPConfig(tools=[tools], default_tools=False), telemetry=False)
    async with Client(build_mcp_server(os)) as client:
        surface = await client.list_tools()
        assert {tool.name for tool in surface} == set(tools.functions)
        for tool in surface:
            assert "_agno_run_context" not in tool.inputSchema.get("properties", {})
            assert "user_id" not in tool.inputSchema.get("properties", {})
        result = await client.call_tool(
            "propose_company_task", {"product_id": product["id"], "title": "MCP proposal", "project_id": project["id"]}
        )
        assert not result.is_error
        rows, _ = CompanyManager(db).list_tasks()
        assert rows[0]["status"] == "backlog" and rows[0]["user_id"] is None
        result = await client.call_tool("log_company_decision", {"decision": "MCP decision"})
        assert not result.is_error
        decisions, _ = CompanyManager(db).list_decisions()
        assert decisions[0].agent_id is None
        for forbidden in ["transition_company_task", "accept_company_task", "complete_company_task"]:
            result = await client.call_tool(forbidden, {"task_id": rows[0]["id"]}, raise_on_error=False)
            assert result.is_error


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async", "http"])
async def test_product_manager_runs_tools_with_injected_identity(tmp_path, mode):
    from agno.models.base import Model
    from agno.models.message import MessageMetrics
    from agno.models.response import ModelResponse

    db = SqliteDb(db_file=str(tmp_path / "runtime.db"))
    product = CompanyManager(db).create(name="SDK", user_id="alice")
    project = CompanyManager(db).create_project(product_id=product["id"], name="Release", user_id="alice")

    class PlanningModel(Model):
        def __init__(self):
            super().__init__(id="offline-planner", provider="test")
            self.calls = 0

        def invoke(self, messages, *args, **kwargs):
            prompt = "\n".join(m.content for m in messages if m.role == "system" and isinstance(m.content, str))
            assert "Human review decision" in prompt
            assert "`log_company_decision`" in prompt and "`search_company_decisions`" in prompt
            assert not any(name in prompt for name in ("`log_decision`", "`search_decisions`", "`record_outcome`"))
            assert "append-only" in prompt
            self.calls += 1
            if self.calls == 1:
                calls = [
                    (
                        "propose_company_task",
                        {
                            "product_id": product["id"],
                            "title": "Draft notes",
                            "project_id": project["id"],
                            "_agno_run_context": {"user_id": "mallory"},
                        },
                    ),
                    (
                        "update_company_status",
                        {"product_id": product["id"], "content": "Draft proposed", "expected_version": 1},
                    ),
                    ("log_company_decision", {"decision": "Review first", "reasoning": "Approval required"}),
                ]
                return ModelResponse(
                    role="assistant",
                    tool_calls=[
                        {
                            "id": str(i),
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)},
                        }
                        for i, (name, arguments) in enumerate(calls)
                    ],
                    response_usage=MessageMetrics(),
                )
            return ModelResponse(role="assistant", content="Proposal recorded", response_usage=MessageMetrics())

        async def ainvoke(self, *args, **kwargs):
            return self.invoke(*args, **kwargs)

        def invoke_stream(self, *args, **kwargs):
            yield self.invoke(*args, **kwargs)

        async def ainvoke_stream(self, *args, **kwargs):
            yield self.invoke(*args, **kwargs)

        def parse_args(self, *args, **kwargs):
            return {}

        def _parse_provider_response(self, response, **kwargs):
            return response

        def _parse_provider_response_delta(self, response):
            return response

    os = AgentOS(db=db, company=CompanyConfig(model=PlanningModel()), user_isolation=True, telemetry=False)
    with TestClient(os.get_app()) as client:
        response = client.post("/company/decisions", json={"decision": "Human review decision"})
        assert response.status_code == 201 and response.json()["agent_id"] is None
    if mode == "http":
        with TestClient(os.get_app()) as client:
            route = "/agents/" + PRODUCT_MANAGER_ID
            assert client.get(route).status_code == 200
            response = client.post(
                route + "/runs",
                data={"message": "Plan the release", "user_id": "alice", "session_id": "planning", "stream": "false"},
            )
            assert response.status_code == 200, response.text
            assert response.json()["content"] == "Proposal recorded"
            created = client.post(
                "/components",
                json={"component_id": PRODUCT_MANAGER_ID, "component_type": "agent", "name": "Impersonator"},
            )
            assert created.status_code == 409, created.text
            assert client.patch("/components/" + PRODUCT_MANAGER_ID, json={"name": "Changed"}).status_code == 404
            assert client.delete("/components/" + PRODUCT_MANAGER_ID).status_code == 404
            assert db.get_component(PRODUCT_MANAGER_ID) is None
            assert client.get(route).status_code == 200
    elif mode == "async":
        await os.product_manager.arun("Plan the release", user_id="alice", session_id="planning")
    else:
        os.product_manager.run("Plan the release", user_id="alice", session_id="planning")
    m = CompanyManager(db)
    tasks, total = m.list_tasks()
    assert total == 1 and tasks[0]["user_id"] == "alice" and tasks[0]["status"] == "backlog"
    assert m.read_wiki(product["id"], "status.md").content == "Draft proposed"
    decisions, total = m.list_decisions()
    assert total == 2
    own = next(decision for decision in decisions if decision.decision == "Review first")
    assert own.user_id == "alice" and own.session_id == "planning" and own.agent_id == PRODUCT_MANAGER_ID
    assert m.list_decisions(agent_id=PRODUCT_MANAGER_ID)[1] == 1


@pytest.mark.asyncio
async def test_tools_and_automatic_recall_require_scopes(tmp_path):
    from agno.company.decisions import CompanyDecisionLogStore
    from agno.os.authz.provider import AuthorizationContext
    from agno.os.authz.scope_provider import ScopeAuthorizationProvider
    from agno.run.authorization import RunAuthorization, authorization_scope

    db = SqliteDb(db_file=str(tmp_path / "permission.db"))
    authority = RunAuthorization(
        provider=ScopeAuthorizationProvider(),
        context=AuthorizationContext(principal_id="alice", scopes=["agents:run"]),
        enforce_tools=False,
    )
    tools = CompanyTools(db, user_isolation=True)
    context = RunContext(run_id="r", session_id="s", user_id="spoofed", authorization=authority)
    with authorization_scope(lambda: authority):
        with pytest.raises(PermissionError):
            tools.list_company_products(_agno_run_context=context)
        with pytest.raises(PermissionError):
            await tools.alog_company_decision("denied", _agno_run_context=context)
        with pytest.raises(PermissionError):
            CompanyDecisionLogStore(db).recall(run_context=context)
        with pytest.raises(PermissionError):
            await CompanyDecisionLogStore(db).arecall(run_context=context)
    assert CompanyManager(db).list_decisions()[1] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("fresh", [False, True])
async def test_served_product_manager_resolution_and_catalog_fence(tmp_path, fresh):
    from agno.os.utils import AgnoHTTPException, get_agent_by_id, get_agent_by_id_async

    db = SqliteDb(db_file=str(tmp_path / "resolution.db"))
    os = AgentOS(db=db, company=CompanyConfig(model=OpenAIResponses(id="offline")), telemetry=False)
    for resolver in (get_agent_by_id, get_agent_by_id_async):
        result = resolver(PRODUCT_MANAGER_ID, agents=os._agents, db=db, create_fresh=fresh)
        result = await result if inspect.isawaitable(result) else result
        assert result.id == PRODUCT_MANAGER_ID
        assert (result is not os.product_manager) == fresh
        with pytest.raises(AgnoHTTPException, match="reserved"):
            result = resolver(PRODUCT_MANAGER_ID, agents=[], db=db)
            if inspect.isawaitable(result):
                await result
    db.close()
