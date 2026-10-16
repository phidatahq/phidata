"""Publication scopes use the app route map in scope and managed authorization planes."""
# ruff: noqa: F811

from unittest.mock import AsyncMock

import pytest

from tests.unit.os.routers.test_company_execution import accepted, headers, managed_system, system  # noqa: F401


def test_publication_requires_both_scopes(system, monkeypatch):
    client, _, _, _ = system
    path, _ = accepted(client)
    publish = AsyncMock(
        return_value={
            "number": 1,
            "url": "https://github.com/a/b/pull/1",
            "head_sha": "a" * 40,
            "base": "main",
            "branch": "company/task-1",
        }
    )
    monkeypatch.setattr("agno.company.publish.apublish_task", publish)
    for scopes in (["tasks:write"], ["sources:publish"], ["tasks:read", "sources:read"]):
        assert client.post(path + "/publish", headers=headers(scopes=scopes)).status_code == 403
    publish.assert_not_called()
    response = client.post(path + "/publish", headers=headers(scopes=["tasks:write", "sources:publish"]))
    assert response.status_code == 202, response.text
    assert publish.await_count == 1


def test_publication_managed_role_overrides_token_scopes(managed_system, monkeypatch):
    client, _, _, _, authz = managed_system
    path, _ = accepted(client)
    publish = AsyncMock(return_value={"number": 1})
    monkeypatch.setattr("agno.company.publish.apublish_task", publish)
    assert client.post(path + "/publish", headers=headers(scopes=["agent_os:admin"])).status_code == 403
    publish.assert_not_called()
    authz.define_role("publisher", ["tasks:write", "sources:publish"])
    authz.set_role("alice", "publisher")
    response = client.post(path + "/publish", headers=headers(scopes=[]))
    assert response.status_code == 202, response.text
    assert publish.await_count == 1


@pytest.mark.parametrize("ref", ["GITHUB_READ_TOKEN", "actual-secret-value!", ""])
def test_invalid_publication_credential_reference(ref):
    from agno.company.declarations import Source

    with pytest.raises(ValueError):
        Source(
            type="git",
            reference="https://github.com/a/b",
            credential_ref="GITHUB_READ_TOKEN",
            config={"publish_credential_ref": ref},
        )


@pytest.mark.asyncio
async def test_automatic_publication_rechecks_saved_managed_identity(managed_system, monkeypatch):
    from agno.company.routines import _CompanyScheduleExecutor
    from agno.run.authorization import current_authorization

    client, db, os, _, authz = managed_system
    _, task = accepted(client)
    task = db.start_task_run(task["id"], 1, db.get_task(task["id"])["transitions"])
    task = db.complete_task_run(task["id"], task["job_id"], {"status": "COMPLETED", "pr": {"number": 1}})

    async def policy(*args):
        return {"publish": True, "required_checks": []}

    calls = []

    async def publish(*args, **kwargs):
        authority = current_authorization()
        assert authority.context.principal_id == "alice"
        await authority.arequire("tasks", "write")
        await authority.arequire("sources", "publish")
        calls.append("published")
        return {"number": 1}

    monkeypatch.setattr("agno.company.publish._policy", policy)
    monkeypatch.setattr("agno.company.publish.areconcile_task", AsyncMock(return_value=task))
    monkeypatch.setattr("agno.company.publish.apublish_task", publish)
    authz.define_role("without_publish", ["tasks:write", "schedules:write"])
    authz.define_role("with_publish", ["tasks:write", "schedules:write", "sources:publish"])
    executor = _CompanyScheduleExecutor(
        os, client.app, base_url="http://test", internal_service_token="company-internal"
    )
    authz.set_role("alice", "without_publish")
    with pytest.raises(PermissionError, match="sources:publish"):
        await executor._review(task)
    assert not calls
    authz.set_role("alice", "with_publish")
    assert (await executor._review(task))["action"] == "published"
    authz.set_role("alice", "without_publish")
    with pytest.raises(PermissionError, match="sources:publish"):
        await executor._review(task)
    assert calls == ["published"]


def test_enabling_automatic_publication_requires_publish_permission(system):
    from tests.unit.os.routers.test_company_execution import SCOPES

    client, _, _, _ = system
    product = client.post("/company/products", json={"name": "Publish policy"}, headers=headers()).json()
    body = {
        "product_id": product["id"],
        "name": "publisher",
        "template": "intake",
        "executor_type": "agent",
        "executor_id": "writer",
        "cron_expr": "0 * * * *",
        "auto_accept": {
            "executor_type": "agent",
            "executor_id": "writer",
            "publish": True,
            "required_checks": ["executor_registered"],
            "limits": {"expires_at": 4102444800},
        },
    }
    scopes = [*SCOPES, "routines:write", "schedules:write"]
    assert client.post("/company/routines", json=body, headers=headers(scopes=scopes)).status_code == 403
    response = client.post("/company/routines", json=body, headers=headers(scopes=[*scopes, "sources:publish"]))
    assert response.status_code == 201, response.text
    assert response.json()["payload"]["metadata"]["auto_accept"]["publish"] is True

    body["auto_accept"]["required_checks"] = ["unit-tests"]
    unknown = client.post("/company/routines", json=body, headers=headers(scopes=[*scopes, "sources:publish"]))
    assert unknown.status_code == 422, unknown.text
    assert "Unknown automatic acceptance check" in unknown.text
