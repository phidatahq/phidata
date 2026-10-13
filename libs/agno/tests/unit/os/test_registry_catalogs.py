"""Catalogs: named, stored sets of registry entries granted by catalogs:<slug>:read."""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

import jwt
import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, Authorization
from agno.registry import Registry

JWT_SECRET = "test-secret-key-at-least-256-bits-long-000"
OS_ID = "registry-catalogs-test-os"


def search(query: str) -> str:
    """Search the web."""
    return query


def sql(query: str) -> str:
    """Run a SQL query."""
    return query


def slack(message: str) -> str:
    """Post to Slack."""
    return message


def _tool(*names: str) -> List[Dict[str, str]]:
    return [{"type": "tool", "name": name} for name in names]


def _token(scopes: Optional[List[str]] = None, org_id: Optional[str] = None, sub: str = "user") -> str:
    payload: Dict[str, Any] = {
        "sub": sub,
        "aud": OS_ID,
        "scopes": scopes or [],
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    if org_id is not None:
        payload["org_id"] = org_id
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _authorization(db_file: str) -> Authorization:
    authz = Authorization(
        db=SqliteDb(db_file=db_file),
        verification_keys=[JWT_SECRET],
        algorithm="HS256",
        verify_audience=True,
        audience=OS_ID,
        roles_claim="org_id",
        trust_token_scopes=True,
    )
    authz.define_role("acme", ["catalogs:starter:read", "catalogs:analytics:read"])
    authz.define_role("globex", ["catalogs:starter:read"])
    return authz


def _client(authz: Authorization) -> TestClient:
    agent_os = AgentOS(
        id=OS_ID,
        agents=[Agent(id="support-agent", name="Support Agent")],
        registry=Registry(tools=[search, sql, slack]),
        authorization=authz,
        telemetry=False,
    )
    return TestClient(agent_os.get_app())


@pytest.fixture
def authz(tmp_path) -> Authorization:
    return _authorization(str(tmp_path / "authz.db"))


@pytest.fixture
def client(authz) -> TestClient:
    client = _client(authz)
    authz.set_catalog("starter", _tool("search"))
    authz.set_catalog("analytics", _tool("sql"))
    return client


ADMIN = {"Authorization": f"Bearer {_token(['agent_os:admin'], sub='operator')}"}


def _names(client: TestClient, token: str, **params: str) -> List[str]:
    response = client.get(
        "/registry", params={"resource_type": "tool", **params}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    return sorted(item["name"] for item in response.json()["data"])


class TestRegistryListing:
    def test_a_caller_lists_the_entries_of_every_catalog_it_holds(self, client):
        assert _names(client, _token(org_id="acme")) == ["search", "sql"]
        assert _names(client, _token(org_id="globex")) == ["search"]

    def test_a_caller_with_no_catalog_lists_nothing(self, client):
        assert _names(client, _token(org_id="initech")) == []

    def test_a_catalog_scope_on_the_token_grants_it(self, client):
        assert _names(client, _token(["catalogs:analytics:read"])) == ["sql"]

    def test_the_collection_scope_grants_every_catalog(self, client):
        assert _names(client, _token(["catalogs:read"])) == ["search", "sql"]

    def test_catalogs_add_to_entries_granted_directly(self, client):
        assert _names(client, _token(["catalogs:starter:read", "registry:slack:read"])) == ["search", "slack"]

    def test_an_entry_is_matched_by_type_as_well_as_name(self, client, authz):
        authz.set_catalog("functions", [{"type": "function", "name": "slack"}])
        assert _names(client, _token(["catalogs:functions:read"])) == []

    def test_a_shared_catalog_changes_for_every_holder(self, client, authz):
        authz.set_catalog("starter", _tool("search", "slack"))
        assert _names(client, _token(org_id="acme")) == ["search", "slack", "sql"]
        assert _names(client, _token(org_id="globex")) == ["search", "slack"]

    def test_a_removed_catalog_grants_nothing(self, client, authz):
        assert authz.remove_catalog("starter") is True
        assert _names(client, _token(org_id="globex")) == []

    def test_the_catalog_parameter_lists_one_catalog(self, client):
        assert _names(client, _token(org_id="acme"), catalog="analytics") == ["sql"]

    def test_a_catalog_the_caller_does_not_hold_is_not_found(self, client):
        headers = {"Authorization": f"Bearer {_token(org_id='globex')}"}
        held_by_others = client.get("/registry", params={"catalog": "analytics"}, headers=headers)
        unknown = client.get("/registry", params={"catalog": "nope"}, headers=headers)
        assert held_by_others.status_code == unknown.status_code == 404


class TestCatalogApi:
    def test_an_admin_builds_reads_and_deletes_a_catalog(self, client):
        response = client.put(
            "/authz/catalogs/support",
            headers=ADMIN,
            json={"name": "Support", "description": "Tools for support", "entries": _tool("slack", "search")},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["slug"] == "support"
        assert body["name"] == "Support"
        assert body["entries"] == _tool("slack", "search")
        assert body["scope"] == "catalogs:support:read"

        assert client.get("/authz/catalogs/support", headers=ADMIN).json()["entries"] == _tool("slack", "search")
        listed = client.get("/authz/catalogs", headers=ADMIN).json()["data"]
        assert [catalog["slug"] for catalog in listed] == ["analytics", "starter", "support"]

        assert client.delete("/authz/catalogs/support", headers=ADMIN).status_code == 200
        assert client.get("/authz/catalogs/support", headers=ADMIN).status_code == 404
        assert client.delete("/authz/catalogs/support", headers=ADMIN).status_code == 404

    def test_a_built_catalog_applies_to_the_next_listing(self, client):
        client.put("/authz/catalogs/starter", headers=ADMIN, json={"entries": _tool("search", "slack")})
        assert _names(client, _token(org_id="globex")) == ["search", "slack"]

    def test_an_unknown_resource_type_is_rejected(self, client):
        response = client.put("/authz/catalogs/bad", headers=ADMIN, json={"entries": [{"type": "gadget", "name": "x"}]})
        assert response.status_code == 422

    def test_a_slug_that_cannot_be_a_scope_segment_is_rejected(self, client):
        response = client.put("/authz/catalogs/a:b", headers=ADMIN, json={"entries": _tool("search")})
        assert response.status_code == 422

    def test_a_tenant_cannot_read_or_build_catalogs(self, client):
        headers = {"Authorization": f"Bearer {_token(org_id='globex')}"}
        assert client.get("/authz/catalogs", headers=headers).status_code == 403
        response = client.put("/authz/catalogs/starter", headers=headers, json={"entries": _tool("sql")})
        assert response.status_code == 403


class TestCatalogStore:
    def test_catalogs_are_stored_in_the_database(self, tmp_path):
        db_file = str(tmp_path / "authz.db")
        first = _authorization(db_file)
        _client(first)
        first.set_catalog("starter", _tool("search"), name="Starter")

        second = _authorization(db_file)
        _client(second)
        assert second.get_catalog("starter")["entries"] == _tool("search")
        assert second.get_catalog("starter")["name"] == "Starter"

    def test_replacing_a_catalog_keeps_its_creation_time(self, client, authz):
        created_at = authz.get_catalog("starter")["created_at"]
        authz._store()._meta_db.upsert_authz_catalog(
            "starter", {"name": "starter", "description": None, "entries": "[]", "created_at": 1, "updated_at": 2}
        )
        replaced = authz.get_catalog("starter")
        assert replaced["created_at"] == created_at
        assert replaced["updated_at"] == 2
        assert replaced["entries"] == []

    def test_duplicate_entries_are_dropped(self, client, authz):
        catalog = authz.set_catalog("dupes", _tool("search", "search", "sql"))
        assert catalog["entries"] == _tool("search", "sql")

    @pytest.mark.parametrize("slug", ["", "*", "has space", "a/b", "a:b"])
    def test_an_invalid_slug_is_refused(self, client, authz, slug):
        with pytest.raises(ValueError):
            authz.set_catalog(slug, _tool("search"))

    def test_an_entry_without_a_name_is_refused(self, client, authz):
        with pytest.raises(ValueError, match="name"):
            authz.set_catalog("bad", [{"type": "tool", "name": ""}])

    @pytest.mark.asyncio
    async def test_the_async_variants_match_the_sync_ones(self, client, authz):
        await authz.aset_catalog("support", _tool("slack"))
        assert await authz.aget_catalog("support") == authz.get_catalog("support")
        assert await authz.alist_catalogs() == authz.list_catalogs()
        assert await authz.aremove_catalog("support") is True
        assert await authz.aremove_catalog("support") is False
        assert authz.get_catalog("support") is None
