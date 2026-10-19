"""RunOutput.from_dict hands back the status enum that readers such as print_response expect."""

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


def test_from_dict_returns_the_status_enum_for_team_output():
    restored = TeamRunOutput.from_dict({"run_id": "t1", "status": "COMPLETED", "content": "x"})
    assert restored.status is RunStatus.completed
    assert restored.status.value == "COMPLETED"


def test_from_dict_keeps_an_unknown_status_string_for_the_workflow_classes():
    team_restored = TeamRunOutput.from_dict({"run_id": "t1", "status": "SOMETHING_NEW"})
    assert team_restored.status == "SOMETHING_NEW"
    workflow_restored = WorkflowRunOutput.from_dict({"run_id": "w1", "status": "SOMETHING_NEW"})
    assert workflow_restored.status == "SOMETHING_NEW"


def test_round_trip_keeps_the_enum_for_the_workflow_classes():
    original_team = TeamRunOutput(run_id="t1", status=RunStatus.cancelled)
    assert TeamRunOutput.from_dict(original_team.to_dict()).status is RunStatus.cancelled
    original_workflow = WorkflowRunOutput(run_id="w1", status=RunStatus.cancelled)
    assert WorkflowRunOutput.from_dict(original_workflow.to_dict()).status is RunStatus.cancelled
