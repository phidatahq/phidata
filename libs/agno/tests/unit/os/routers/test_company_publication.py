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
