"""Sandbox capability and Source validation require no model or network."""

import pytest
from pydantic import ValidationError

from agno.agent import Agent
from agno.company.sandbox import _accept_sandbox, _is_sandboxed
from agno.company.sources import browse_source, read_source
from agno.db.schemas.sources import validate_source_fields
from agno.db.schemas.tasks import task_run_fields, validate_task_fields
from agno.os.routers.company.schema import TaskCreate, TaskTransition, TaskUpdate
from agno.sandbox import Repository
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.fixture import FixtureAgent


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b",
        "https://gitlab.com/a/b",
        "https://github.com/a/b/tree/main",
        "https://token@github.com/a/b",
        "git@github.com:a/b",
        "https://github.com/a/b?token=x",
    ],
)
def test_git_url_uses_repository_validation(url):
    with pytest.raises(ValueError):
        validate_source_fields({"type": "git", "reference": url})


@pytest.mark.parametrize("branch", ["-main", "HEAD", "foo..bar", "x.lock", "with space"])
def test_git_branch_validation(branch):
    with pytest.raises(ValueError):
        validate_source_fields({"type": "git", "reference": "https://github.com/a/b", "config": {"branch": branch}})


def test_url_source_is_not_read_over_http():
    source = {"id": "git", "type": "git", "reference": "https://github.com/a/b", "config": {"branch": "main"}}
    validate_source_fields({key: value for key, value in source.items() if key != "id"})
    for read in (read_source, browse_source):
        with pytest.raises(ValueError, match="HTTP reading is not supported"):
            read(source, "run")


def test_retired_executor_and_derived_capability():
    with pytest.raises(ValueError):
        validate_task_fields({"executor_type": "engineering"})
    for schema, fields in [
        (TaskCreate, {"product_id": "p", "project_id": "pr", "title": "t"}),
        (TaskUpdate, {}),
        (TaskTransition, {"target": "ready", "reason": "ok", "executor_id": "a"}),
    ]:
        with pytest.raises(ValidationError):
            schema(**fields, executor_type="engineering")
    with pytest.raises(ValueError, match="registered"):
        task_run_fields({"status": "ready", "executor_id": "a", "executor_type": "engineering"}, 1, None)
    assert _is_sandboxed(Agent()) is False
    agent = FixtureAgent(
        sandbox=DockerSandbox("unused", env={"AGNO_SANDBOX_TEST_RUNTIME": "1"}),
        repository=Repository("https://github.com/a/b"),
    )
    assert _is_sandboxed(agent) is True
    with pytest.raises(ValueError, match="GITHUB_READ_TOKEN"):
        _accept_sandbox(
            agent, [{"id": "s", "type": "git", "reference": agent.repository.url, "credential_ref": "GITHUB_TOKEN"}]
        )


@pytest.mark.parametrize("field", ["sandboxed", "metadata"])
def test_task_checkout_and_capability_are_read_only(field):
    with pytest.raises(ValidationError):
        TaskCreate(product_id="p", project_id="pr", title="t", **{field: True})
    with pytest.raises(ValidationError):
        TaskUpdate(**{field: True})
