"""Modal installed-SDK call contracts; no account access."""

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("modal")

import modal

from agno.sandbox.base import SandboxError, SandboxSpec
from agno.sandbox.modal import ModalSandboxProvider
from tests.unit.sandbox.test_hosted import Journal


def method(result=None):
    return SimpleNamespace(aio=AsyncMock(return_value=result))


def provider():
    return ModalSandboxProvider("tests", Journal(), app_name="existing-app")


def sandbox(**kwargs):
    values = dict(object_id="sb-fixture", poll=method(None), get_tags=method({"token": "intent"}), terminate=method(0))
    values.update(kwargs)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_create_uses_actual_sdk_signature_and_root_prepared_image(monkeypatch):
    value = provider()
    lookup = AsyncMock(return_value=SimpleNamespace(app_id="ap-fixture"))
    monkeypatch.setattr(modal.App.lookup, "aio", lookup)
    signature = inspect.signature(modal.Sandbox.create.aio)
    calls = []

    async def create(*args, **kwargs):
        signature.bind(*args, **kwargs)
        calls.append(kwargs)
        assert isinstance(kwargs["image"], modal.Image)
        return sandbox()

    monkeypatch.setattr(modal.Sandbox.create, "aio", create)
    result = await value._create(
        SandboxSpec("a", "s", 1, "python:3.12-slim", pids_limit=None, workspace_mb=None),
        {"name": "logical", "token": "intent"},
    )
    assert result.provider_ref == "sb-fixture"
    lookup.assert_awaited_once_with("existing-app", environment_name=None, create_if_missing=False)
    assert calls[0]["cpu"] == (2.0, 2.0) and calls[0]["memory"] == (2048, 2048)
    assert calls[0]["block_network"] is True
    assert calls[0]["include_oidc_identity_token"] is False
    assert calls[0]["runtime"] == "gvisor"
    assert calls[0]["env"] == {}


@pytest.mark.asyncio
async def test_terminated_compute_never_executes(monkeypatch):
    value = provider()
    compute = sandbox(poll=method(137), exec=method())
    monkeypatch.setattr(modal.Sandbox.from_id, "aio", AsyncMock(return_value=compute))
    assert await value._get("sb-fixture") is None
    with pytest.raises(SandboxError, match="terminated"):
        await value._command("sb-fixture", ["true"], timeout=1)
    compute.exec.aio.assert_not_awaited()


@pytest.mark.asyncio
async def test_termination_waits_for_remote_exit(monkeypatch):
    value = provider()
    compute = sandbox()
    monkeypatch.setattr(modal.Sandbox.from_id, "aio", AsyncMock(return_value=compute))
    await value._delete("sb-fixture")
    compute.terminate.aio.assert_awaited_once_with(wait=True)


@pytest.mark.asyncio
async def test_stat_bounds_download_before_materializing_bytes(monkeypatch):
    value = provider()
    files = SimpleNamespace(stat=method(SimpleNamespace(size=100)), read_bytes=method(b"x" * 100))
    monkeypatch.setattr(value, "_sandbox", AsyncMock(return_value=sandbox(filesystem=files)))
    with pytest.raises(SandboxError, match="byte limit"):
        await value._read("sb-fixture", "/root-object", max_bytes=10)
    files.read_bytes.aio.assert_not_awaited()


@pytest.mark.asyncio
async def test_inventory_is_scoped_to_existing_application_and_token(monkeypatch):
    value = provider()
    monkeypatch.setattr(value, "_app", AsyncMock(return_value=SimpleNamespace(app_id="ap-fixture")))

    async def listing(**kwargs):
        assert kwargs == {"app_id": "ap-fixture", "tags": {"namespace": "modal:tests", "token": "intent"}}
        yield sandbox()
        yield sandbox(poll=method(0))

    monkeypatch.setattr(modal.Sandbox.list, "aio", listing)
    found = await value._inventory("intent")
    assert len(found) == 1
