"""A token's denies claim is enforced on every path that reads JWT scopes."""

import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, CompanyConfig
from agno.os.config import AuthorizationConfig
from agno.os.mcp_auth import _build_jwt_token_verifier

SECRET = "denies-claim-test-secret-at-least-32-bytes"


@pytest.fixture
def agent_os(tmp_path):
    return AgentOS(
        id="denies-test",
        db=SqliteDb(db_file=str(tmp_path / "app.db")),
        company=CompanyConfig(),
        authorization=True,
        authorization_config=AuthorizationConfig(verification_keys=[SECRET], algorithm="HS256"),
        telemetry=False,
    )


@pytest.fixture
def client(agent_os):
    return TestClient(agent_os.get_app())


def _token(agent_os, scopes, denies=None):
    payload = {
        "sub": "user",
        "aud": agent_os.id,
        "scopes": scopes,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    if denies is not None:
        payload["denies"] = denies
    return jwt.encode(payload, SECRET, algorithm="HS256")


def _headers(agent_os, scopes, denies=None):
    return {"Authorization": "Bearer " + _token(agent_os, scopes, denies)}


class TestRouteGate:
    def test_admin_without_denies_reaches_the_route(self, agent_os, client):
        response = client.delete("/company/tasks/missing", headers=_headers(agent_os, ["agent_os:admin"]))
        assert response.status_code not in (401, 403)

    def test_admin_deny_blocks_only_the_denied_action(self, agent_os, client):
        headers = _headers(agent_os, ["agent_os:admin"], ["tasks:delete"])
        assert client.delete("/company/tasks/missing", headers=headers).status_code == 403
        assert client.get("/company/tasks", headers=headers).status_code == 200

    def test_wildcard_allow_with_per_id_deny_blocks_that_agent(self, agent_os, client):
        headers = _headers(agent_os, ["agents:*:read"], ["agents:x:read"])
        assert client.get("/agents/x", headers=headers).status_code == 403

    def test_malformed_denies_claim_grants_nothing(self, agent_os, client):
        headers = _headers(agent_os, ["agent_os:admin"], {"tasks": "delete"})
        assert client.get("/company/tasks", headers=headers).status_code == 403


class TestServiceAccountMinting:
    def _mint(self, client, headers, scopes):
        body = {
            "name": "minted",
            "scopes": [{"scope": s, "effect": "allow"} for s in scopes],
            "allow_privileged_scopes": True,
        }
        return client.post("/service-accounts", json=body, headers=headers)

    def test_cannot_mint_admin_to_escape_a_deny(self, agent_os, client):
        headers = _headers(agent_os, ["agent_os:admin"], ["tasks:delete"])
        assert self._mint(client, headers, ["agent_os:admin"]).status_code == 403

    def test_cannot_mint_the_denied_scope(self, agent_os, client):
        headers = _headers(agent_os, ["agent_os:admin"], ["tasks:delete"])
        assert self._mint(client, headers, ["tasks:delete"]).status_code == 403

    def test_cannot_mint_a_wildcard_covering_a_per_id_deny(self, agent_os, client):
        headers = _headers(agent_os, ["service_accounts:write", "agents:*:run"], ["agents:x:run"])
        assert self._mint(client, headers, ["agents:*:run"]).status_code == 403

    def test_can_still_mint_allowed_scopes(self, agent_os, client):
        headers = _headers(agent_os, ["agent_os:admin"], ["tasks:delete"])
        assert self._mint(client, headers, ["tasks:read"]).status_code == 201


class TestOtherTokenEntryPoints:
    def test_websocket_validator_applies_denies(self, agent_os):
        app = agent_os.get_app()
        payload = jwt.decode(
            _token(agent_os, ["agent_os:admin"], ["tasks:delete"]), options={"verify_signature": False}
        )
        scopes = app.state.jwt_validator.extract_claims(payload)["scopes"]
        assert "agent_os:admin" not in scopes and "tasks:delete" not in scopes
        assert "tasks:write" in scopes

    def test_mcp_jwt_verifier_applies_denies(self, agent_os):
        verifier = _build_jwt_token_verifier(agent_os)
        access_token = asyncio.run(verifier.verify_token(_token(agent_os, ["agents:*:run"], ["agents:x:run"])))
        assert access_token is not None
        assert access_token.scopes == []

    def test_external_mcp_provider_applies_denies(self):
        pytest.importorskip("fastmcp")
        from fastmcp.server.auth import RemoteAuthProvider
        from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
        from pydantic import AnyHttpUrl

        from agno.os.mcp_auth import _MarkerScrubbingProvider

        tokens = {
            "denied": {"client_id": "u", "scopes": ["agents:*:run", "agents:read"], "denies": ["agents:x:run"]},
            "plain": {"client_id": "u", "scopes": ["agents:*:run"]},
        }
        provider = _MarkerScrubbingProvider(
            RemoteAuthProvider(
                token_verifier=StaticTokenVerifier(tokens=tokens),
                authorization_servers=[AnyHttpUrl("https://as.example.com")],
                base_url="http://localhost",
            )
        )
        assert asyncio.run(provider.verify_token("denied")).scopes == ["agents:read"]
        assert asyncio.run(provider.verify_token("plain")).scopes == ["agents:*:run"]


class TestTokensWithoutDenies:
    def test_websocket_and_mcp_scopes_are_unchanged(self, agent_os):
        app = agent_os.get_app()
        token = _token(agent_os, ["agent_os:admin", "agents::run"])
        payload = jwt.decode(token, options={"verify_signature": False})
        assert app.state.jwt_validator.extract_claims(payload)["scopes"] == ["agent_os:admin", "agents::run"]
        access_token = asyncio.run(_build_jwt_token_verifier(agent_os).verify_token(token))
        assert access_token.scopes == ["agent_os:admin", "agents::run"]


class TestClaimsCopies:
    def test_mcp_claims_carry_the_restricted_scopes(self, agent_os):
        access_token = asyncio.run(
            _build_jwt_token_verifier(agent_os).verify_token(_token(agent_os, ["agents:*:run"], ["agents:x:run"]))
        )
        assert access_token.claims["scopes"] == []

    def test_request_state_claims_carry_the_restricted_scopes(self, agent_os):
        from fastapi import Request

        app = agent_os.get_app()

        @app.get("/denies-probe")
        def probe(request: Request):
            return {"scopes": request.state.scopes, "claims_scopes": request.state.claims["scopes"]}

        response = TestClient(app).get(
            "/denies-probe", headers=_headers(agent_os, ["tasks:read", "tasks:delete"], ["tasks:delete"])
        )
        assert response.json() == {"scopes": ["tasks:read"], "claims_scopes": ["tasks:read"]}
