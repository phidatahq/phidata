"""The framework Product Manager uses ordinary AgentOS routes and Company policy."""

import json
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_execution import LocalModel, caller, runtime_os
from test_manual import KEY, SCOPES, mutation, token

from agno.agent import Agent
from agno.models.response import ModelResponse
from agno.os import AgentOS, Authorization, CompanyConfig, QueueConfig
from agno.os.company.schemas import ProductCreate, TaskCreate


class ProductModel(LocalModel):
    def invoke(self, messages, **kwargs):
        responses = [m for m in messages if m.role == "tool"]
        if responses:
            return ModelResponse(role="assistant", content=str(responses[-1].content))
        return ModelResponse(
            role="assistant",
            tool_calls=[
                {
                    "id": str(uuid4()),
                    "type": "function",
                    "function": {"name": "list_products", "arguments": json.dumps({})},
                }
            ],
        )

    async def ainvoke(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)


def builtin_os(setup, *, agents=None, runtime_db=None):
    db, users, _ = setup
    users.attach_db(runtime_db if runtime_db is not None else db)
    return AgentOS(
        id="company-test",
        db=runtime_db,
        agents=agents,
        company=CompanyConfig(db=db, model=ProductModel()),
        user_directory=users,
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256", audience="company-test"),
        queue=QueueConfig(durable=True, poll_interval=0.02) if runtime_db is not None else None,
    )


def test_builtin_is_reused_across_products_and_resync_without_mutating_callers(setup):
    agents = []
    os = builtin_os(setup, agents=agents)
    manager = os.company.product_manager
    assert agents == []
    assert isinstance(manager, Agent)
    assert manager.id == "product-manager" and manager.db is setup[0]
    assert callable(manager.run) and callable(manager.arun)
    assert [t.name for t in manager.tools] == ["company"]
    assert {"set_review_pull_request", "transition_task", "create_product", "set_schedule"}.isdisjoint(
        manager.tools[0].get_functions()
    )
    app = os.get_app()
    for _ in range(2):
        os.resync(app)
    assert os.company.product_manager is manager
    assert sum(a is manager for a in os.agents) == 1
    for name in ("Documentation", "Website"):
        os.company.create_product(data=ProductCreate(name=name), **mutation())
    assert os.agents == [manager]
    other = builtin_os(setup)
    assert other.company.product_manager is not manager


def test_manual_company_does_not_create_product_manager(setup):
    db, users, _ = setup
    os = AgentOS(
        company=CompanyConfig(db=db),
        authorization=Authorization(verification_keys=[KEY], algorithm="HS256"),
    )
    assert os.company.product_manager is None
    assert not os.agents


def test_builtin_rejects_conflicting_custom_agent_id(setup):
    custom = Agent(id="product-manager", model=LocalModel())
    agents = [custom]
    with pytest.raises(ValueError, match="built-in Product Manager"):
        builtin_os(setup, agents=agents)
    assert agents == [custom]


def test_builtin_http_and_durable_task_runs_keep_initiating_users_access(setup):
    original, _ = runtime_os(setup)
    os = builtin_os(setup, runtime_db=original.db)
    assert os.company.product_manager.db is original.db
    with TestClient(os.get_app()) as client:
        product = os.company.create_product(
            data=ProductCreate(name="Documentation", agent_id="product-manager"), **mutation(principal=caller())
        )
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        response = client.post("/agents/product-manager/runs", data={"message": "List my Products", "stream": "false"})
        assert response.status_code == 200, response.text
        assert "Documentation" in response.json()["content"]
        # A different caller may run the same built-in but cannot see this Product.
        client.headers["Authorization"] = "Bearer " + token(who="mallory", scopes=(*SCOPES, "agents:run"))
        denied = client.post(
            "/agents/product-manager/runs", data={"message": "List my Products", "stream": "false", "user_id": "alice"}
        )
        assert denied.status_code == 200, denied.text
        assert "Documentation" not in denied.json()["content"]
        task = os.company.create_task(
            product_id=product["id"],
            data=TaskCreate(title="Summarize my Products", instructions="List my Products"),
            **mutation(principal=caller()),
        )
        client.headers["Authorization"] = "Bearer " + token(scopes=(*SCOPES, "agents:run"))
        response = client.post(
            f"/company/v1/tasks/{task['id']}/runs",
            json={},
            headers={"Idempotency-Key": "builtin-run", "If-Match": f'"{task["version"]}"'},
        )
        assert response.status_code == 202, response.text
        run_id = response.json()["id"]
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            result = client.get(f"/company/v1/tasks/{task['id']}/runs/{run_id}")
            if result.status_code == 200 and "Documentation" in str(result.json().get("content")):
                break
            time.sleep(0.02)
        assert result.status_code == 200, result.text
        assert "Documentation" in str(result.json()["content"])


def test_model_default_override_and_resolution_is_stable(setup):
    from agno.registry import Registry

    db, _, _ = setup
    first, second = ProductModel(), ProductModel()
    first.id, second.id = "first", "second"
    auth = Authorization(verification_keys=[KEY], algorithm="HS256")
    config = CompanyConfig()
    registry = Registry(models=[first, second])
    os = AgentOS(db=db, registry=registry, company=config, authorization=auth)
    assert os.company.product_manager.model is first
    assert config.db is None and config.model is None
    registry.models.reverse()
    os.resync(os.get_app())
    assert os.company.product_manager.model is first
    overridden = AgentOS(db=db, registry=registry, company=CompanyConfig(model=first), authorization=auth)
    assert overridden.company.product_manager.model is first
