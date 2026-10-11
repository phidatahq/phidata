"""Daytona SDK contract checks without account or network access."""

from types import SimpleNamespace

import pytest

pytest.importorskip("daytona")

from daytona import CreateSandboxFromSnapshotParams, ListSandboxesQuery
from daytona_api_client.models.sandbox_state import SandboxState

from agno.sandbox.base import SandboxError, SandboxSpec
from agno.sandbox.daytona import DaytonaSandboxProvider
from tests.unit.sandbox.test_hosted import Journal


@pytest.fixture
def provider():
    with pytest.warns(DeprecationWarning, match="Polling-only"):
        value = DaytonaSandboxProvider("tests", Journal(), api_key="test-key")
    yield value
    value._client._http_client.close()
    value._client._api_client.rest_client.pool_manager.clear()
    value._client._toolbox_api_client.rest_client.pool_manager.clear()


def sandbox(**kwargs):
    values = dict(
        id="computer",
        state=SandboxState.STARTED,
        labels={"agno_token": "intent", "daytona_language": "python"},
        cpu=2,
        memory=2,
        network_block_all=True,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_both_api_and_command_transport_retries_disabled(provider):
    for client in (provider._client._api_client, provider._client._toolbox_api_client):
        assert client.configuration.retries == 0
        assert client.rest_client.pool_manager.connection_pool_kw["retries"] == 0


@pytest.mark.asyncio
async def test_create_params_preserve_network_lifetime_and_root_transport(provider, monkeypatch):
    calls = []

    def create(params, *, timeout):
        assert isinstance(params, CreateSandboxFromSnapshotParams)
        calls.append(params.model_dump())
        return sandbox(labels={**params.labels, "daytona_language": "python"})

    monkeypatch.setattr(provider._client, "create", create)
    spec = SandboxSpec("a", "s", 1, "snapshot", pids_limit=None, workspace_mb=None, env={"KEY": "explicit"})
    result = await provider._create(spec, {"name": "computer-name", "token": "intent"})
    assert result.metadata == {"name": "computer-name", "token": "intent"}
    assert calls[0]["os_user"] == "root"
    assert calls[0]["network_block_all"] is True and calls[0]["public"] is False
    assert calls[0]["env_vars"] == {"KEY": "explicit"}
    assert calls[0]["ttl_minutes"] == 30
    assert calls[0]["auto_stop_interval"] == calls[0]["auto_pause_interval"] == 0


@pytest.mark.asyncio
async def test_stopped_compute_is_not_started_and_delete_waits(provider, monkeypatch):
    stopped = sandbox(state=SandboxState.STOPPED)
    calls = []
    stopped.delete = lambda **kwargs: calls.append(kwargs)
    monkeypatch.setattr(provider._client, "get", lambda *args, **kwargs: stopped)
    with pytest.raises(SandboxError, match="implicit resume"):
        await provider._command("computer", ["true"], timeout=2)
    await provider._delete("computer")
    assert calls == [{"timeout": 120, "wait": True}]


@pytest.mark.asyncio
async def test_inventory_uses_labels_and_filters_destroyed(provider, monkeypatch):
    def listing(query, **kwargs):
        assert isinstance(query, ListSandboxesQuery)
        assert query.labels == {"agno_namespace": "daytona:tests", "agno_token": "intent"}
        yield sandbox()
        yield sandbox(state=SandboxState.DESTROYED)

    monkeypatch.setattr(provider._client, "list", listing)
    found = await provider._inventory("intent")
    assert len(found) == 1 and found[0].state == "running"


@pytest.mark.asyncio
async def test_stream_limit_closes_download_generator(provider, monkeypatch):
    closed = []

    def stream(*args, **kwargs):
        try:
            yield b"too-large"
        finally:
            closed.append(True)

    fs = SimpleNamespace(get_file_info=lambda *a, **k: SimpleNamespace(size=1), download_file_stream=stream)
    monkeypatch.setattr(provider, "_sandbox", lambda *args, **kwargs: sandbox(fs=fs))
    with pytest.raises(SandboxError, match="byte limit"):
        await provider._read("computer", "path", max_bytes=2)
    assert closed == [True]
