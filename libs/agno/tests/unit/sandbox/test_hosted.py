import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest

from agno.sandbox.allocation import SandboxAllocationUnknown
from agno.sandbox.base import ExecResult, SandboxError, SandboxSpec
from agno.sandbox.hosted import HostedComputer, HostedSandboxProvider


class Journal:
    def __init__(self):
        self.rows = {}

    async def ainspect(self, namespace, name):
        row = self.rows.get((namespace, name))
        return dict(row) if row else None

    async def _reserve(self, namespace, name, digest, *, max_allocations):
        row = self.rows.get((namespace, name))
        if row and row["state"] != "retired":
            return dict(row), False
        row = dict(name=name, digest=digest, token=uuid4().hex, state="pending", provider_ref=None)
        self.rows[namespace, name] = row
        return dict(row), True

    async def _bind(self, namespace, name, token, provider_ref):
        row = self.rows[namespace, name]
        assert row["token"] == token
        row.update(provider_ref=provider_ref, state="ready")

    async def _retire(self, namespace, name, token, provider_ref):
        row = self.rows[namespace, name]
        assert row["token"] == token and row["provider_ref"] == provider_ref
        row["state"] = "retired"


class Provider(HostedSandboxProvider):
    backend = "fixture"

    def __init__(self):
        super().__init__("deployment", Journal())
        self.computers = {}
        self.creates = 0
        self.lost_create = False
        self.hide_inventory = False
        self.failed_command = False
        self.deletes = []

    async def _create(self, spec, metadata):
        self.creates += 1
        computer = HostedComputer(uuid4().hex, metadata, "running")
        self.computers[computer.provider_ref] = computer
        if self.lost_create:
            raise TimeoutError("lost create")
        return computer

    async def _get(self, provider_ref):
        return self.computers.get(provider_ref)

    async def _inventory(self, token):
        return [] if self.hide_inventory else [v for v in self.computers.values() if v.metadata["token"] == token]

    async def _delete(self, provider_ref):
        self.deletes.append(provider_ref)
        self.computers.pop(provider_ref)

    async def _command(self, provider_ref, argv, *, timeout):
        if self.failed_command:
            raise TimeoutError("lost command")
        return ExecResult(0, "{}", "")

    async def _write(self, provider_ref, path, payload):
        pass

    async def _read(self, provider_ref, path, *, max_bytes):
        return b""


def spec():
    return SandboxSpec("a", "s", 1, "prepared", pids_limit=None, workspace_mb=None)


@pytest.mark.asyncio
async def test_lost_create_is_reconciled_without_reallocation():
    provider = Provider()
    provider.lost_create = True
    with pytest.raises(TimeoutError):
        await provider.acreate(spec())
    provider.hide_inventory = True
    with pytest.raises(SandboxAllocationUnknown):
        await provider.acreate(spec())
    assert provider.creates == 1
    provider.hide_inventory = False
    found = await provider.afind(spec())
    assert found == await provider.acreate(spec())
    assert provider.creates == 1


@pytest.mark.asyncio
async def test_duplicate_inventory_and_foreign_metadata_fail_closed():
    provider = Provider()
    provider.lost_create = True
    with pytest.raises(TimeoutError):
        await provider.acreate(spec())
    original = next(iter(provider.computers.values()))
    provider.computers["second"] = replace(original, provider_ref="second")
    with pytest.raises(SandboxAllocationUnknown):
        await provider.afind(spec())
    provider.computers.pop("second")
    provider.computers[original.provider_ref] = replace(original, metadata={**original.metadata, "session": "foreign"})
    with pytest.raises(SandboxAllocationUnknown):
        await provider.afind(spec())
    assert not provider.deletes


@pytest.mark.asyncio
async def test_control_failure_keeps_compute_but_command_failure_stops_it():
    provider = Provider()
    handle = await provider.acreate(spec())
    provider.failed_command = True
    with pytest.raises(TimeoutError):
        await provider.arpc(handle, "poll", b"{}")
    assert not provider.deletes
    with pytest.raises(TimeoutError):
        await provider.aexec(handle, ["example"])
    assert provider.deletes == [handle.provider_ref]
    await provider.adestroy(handle)
    assert provider.deletes == [handle.provider_ref]


@pytest.mark.asyncio
async def test_cancelled_create_drains_then_reconciles():
    provider = Provider()
    entered, finish = asyncio.Event(), asyncio.Event()
    original = provider._create

    async def delayed(*args):
        entered.set()
        await finish.wait()
        return await original(*args)

    provider._create = delayed
    task = asyncio.create_task(provider.acreate(spec()))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await provider.afind(spec()) is not None
    assert provider.creates == 1


@pytest.mark.asyncio
async def test_stale_generation_never_deletes_live_compute():
    provider = Provider()
    handle = await provider.acreate(spec())
    with pytest.raises(SandboxError, match="identity"):
        await provider.adestroy(replace(handle, generation=2))
    assert not provider.deletes


@pytest.mark.asyncio
async def test_resource_validation_failure_reclaims_bound_allocation():
    provider = Provider()

    async def reject(*args):
        raise SandboxError("template resources differ")

    provider._check_resources = reject
    with pytest.raises(SandboxError, match="resources"):
        await provider.acreate(spec())
    assert len(provider.deletes) == 1
    assert next(iter(provider.journal.rows.values()))["state"] == "retired"


@pytest.mark.asyncio
async def test_ready_allocation_cannot_be_relabelled_to_another_session():
    provider = Provider()
    handle = await provider.acreate(spec())
    computer = provider.computers[handle.provider_ref]
    provider.computers[handle.provider_ref] = replace(computer, metadata={**computer.metadata, "session": "other"})
    with pytest.raises(SandboxAllocationUnknown, match="metadata"):
        await provider.afind(spec())
    assert not provider.deletes
