"""RunOutput, TeamRunOutput, and WorkflowRunOutput.from_dict hand back the status enum."""

import pytest

from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from agno.run.team import TeamRunOutput
from agno.run.workflow import WorkflowRunOutput


def test_from_dict_returns_the_status_enum():
    restored = RunOutput.from_dict({"run_id": "r1", "status": "COMPLETED", "content": "x"})
    assert restored.status is RunStatus.completed
    assert restored.status.value == "COMPLETED"


def test_from_dict_keeps_an_unknown_status_string():
    restored = RunOutput.from_dict({"run_id": "r1", "status": "SOMETHING_NEW"})
    assert restored.status == "SOMETHING_NEW"


def test_round_trip_keeps_the_enum():
    original = RunOutput(run_id="r1", status=RunStatus.cancelled)
    assert RunOutput.from_dict(original.to_dict()).status is RunStatus.cancelled


@pytest.mark.parametrize("cls", [TeamRunOutput, WorkflowRunOutput])
def test_team_and_workflow_from_dict_return_status_enum(cls):
    for status_member in RunStatus:
        instance = cls(run_id="r1", status=status_member)
        restored = cls.from_dict(instance.to_dict())
        assert restored.status is status_member
        assert isinstance(restored.status, RunStatus)
        assert restored.status.value == status_member.value


@pytest.mark.parametrize("cls", [TeamRunOutput, WorkflowRunOutput])
def test_team_and_workflow_from_dict_keep_unknown_status_string(cls):
    restored = cls.from_dict({"run_id": "r1", "status": "FUTURE_STATUS"})
    assert restored.status == "FUTURE_STATUS"


def test_nested_member_and_step_executor_runs_coerce_status_enum():
    team = TeamRunOutput(
        run_id="t1",
        team_id="team-1",
        status=RunStatus.completed,
        member_responses=[
            RunOutput(run_id="a1", agent_id="agent-1", status=RunStatus.completed),
            TeamRunOutput(run_id="t2", team_id="team-2", status=RunStatus.paused),
        ],
    )
    restored_team = TeamRunOutput.from_dict(team.to_dict())
    assert restored_team.status is RunStatus.completed
    assert restored_team.member_responses[0].status is RunStatus.completed
    assert restored_team.member_responses[1].status is RunStatus.paused

    wf = WorkflowRunOutput(
        run_id="w1",
        workflow_name="wf-main",
        status=RunStatus.completed,
        step_executor_runs=[
            TeamRunOutput(run_id="t1", team_id="team-1", status=RunStatus.completed),
            WorkflowRunOutput(run_id="w2", workflow_name="wf-sub", parent_run_id="w1", status=RunStatus.cancelled),
        ],
    )
    restored_wf = WorkflowRunOutput.from_dict(wf.to_dict())
    assert restored_wf.status is RunStatus.completed
    assert restored_wf.step_executor_runs[0].status is RunStatus.completed
    assert restored_wf.step_executor_runs[1].status is RunStatus.cancelled

