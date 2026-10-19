"""Regression cases from Company operator simulations."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agno.company.routines import _routine_failure


@pytest.mark.parametrize(
    "name", ["read_company_wiki", "update_company_status", "write_company_wiki", "propose_company_project"]
)
def test_routine_required_tool_errors(name):
    output = {
        "member_responses": [
            {"tools": [{"tool_name": name, "tool_call_error": True, "result": "Required operation refused"}]}
        ]
    }
    assert "Required operation refused" in (_routine_failure(output) or "")


def test_routine_blocked_proposal_in_messages():
    output = {
        "messages": [
            {
                "role": "tool",
                "tool_name": "intake_company_source",
                "tool_call_error": True,
                "content": "Tool call limit reached. Tool call intake_company_source not executed. Don't try to execute it again.",
            }
        ]
    }
    assert "limit reached" in (_routine_failure(output) or "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "step",
    [
        {"success": False, "error": "Classifier input budget exceeded"},
        {"status": "CANCELLED", "content": "Classifier cancelled"},
    ],
)
async def test_completed_workflow_projects_failed_step(monkeypatch, step):
    import agno.company.execution as execution

    data = {"run_id": "run", "status": "COMPLETED", "content": "Confident answer", "step_results": [step]}
    output = SimpleNamespace(status="COMPLETED", to_dict=lambda: data)
    component = SimpleNamespace(aget_run_output=AsyncMock(return_value=output))
    worker = SimpleNamespace(_company_db=object(), _aresolve_job_component=AsyncMock(return_value=component))
    monkeypatch.setattr(execution, "_reserve_task", AsyncMock(return_value={"id": "task", "transitions": []}))
    save = AsyncMock()
    monkeypatch.setattr(execution, "_call", save)
    await execution._project_run(
        worker,
        {"id": "run", "session_id": "session", "component_type": "workflow", "payload": {"company_task_id": "task"}},
        "completed",
    )
    result = save.call_args.args[4]
    assert result["status"] == "ERROR"
    assert "Classifier" in result["content"]


def test_saved_newsletter_and_support_transcripts():
    import json
    from pathlib import Path

    from agno.company.execution import _project_workflow_result

    # Retain only the execution evidence needed to reproduce the saved failures.
    fixture = json.loads((Path(__file__).parent / "fixtures" / "company_simulation.json").read_text())
    assert "limit reached" in _routine_failure(fixture["newsletter"])
    result = _project_workflow_result("workflow", fixture["support"], {"status": "COMPLETED"})
    assert result["status"] == "ERROR"
    assert result["content"] == "Northstar call exceeds conservative input budget bound"


@pytest.mark.parametrize("kind", ["agent", "team", "workflow", "external"])
@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_component_capacity_requires_positive_integer(kind, limit):
    from agno.agent import Agent
    from agno.agents.codex import CodexAgent
    from agno.team import Team
    from agno.workflow import Workflow

    cls = {"agent": Agent, "team": Team, "workflow": Workflow, "external": CodexAgent}[kind]
    with pytest.raises(ValueError, match="max_concurrent_runs"):
        cls(max_concurrent_runs=limit, **({"members": []} if kind == "team" else {}))


@pytest.mark.parametrize("kind", ["agent", "team", "workflow"])
def test_component_capacity_survives_serialization(kind):
    from agno.agent import Agent
    from agno.team import Team
    from agno.workflow import Workflow

    cls = {"agent": Agent, "team": Team, "workflow": Workflow}[kind]
    component = cls(id="bounded", max_concurrent_runs=2, **({"members": []} if kind == "team" else {}))
    restored = cls.from_dict(component.to_dict())
    assert restored.max_concurrent_runs == 2
