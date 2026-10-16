"""Compatibility contract for the temporary private checkpoint-store bridge."""

from dataclasses import asdict
from types import SimpleNamespace

import pytest

from agno.company.checkpoints import _checkpoint_store, open_run_checkpoint, open_run_checkpoint_sync
from agno.db.postgres import PostgresDb
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.fixture import FixtureAgent


@pytest.fixture
def completed(tmp_path):
    store = FileCheckpointStore(tmp_path / "store")
    agent = FixtureAgent(
        id="engineer",
        db=PostgresDb(db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
        sandbox=DockerSandbox("unused", checkpoints=store, env={"AGNO_SANDBOX_TEST_RUNTIME": "1"}),
    )
    archive = tmp_path / "object"
    archive.write_bytes(b"archive")
    row = {
        "agent_id": agent.id,
        "status": "COMPLETED",
        "run_data": {"metadata": {"sandbox": {"checkpoint": asdict(store.put(archive))}}},
    }
    return agent, row


def test_private_coordinator_name_and_store_resolution(completed):
    from agno.sandbox._harness import coordinator

    agent, row = completed
    assert callable(coordinator)
    assert _checkpoint_store(agent) is coordinator(agent).transfer.store is agent.sandbox.checkpoints
    with open_run_checkpoint_sync(agent, row) as path:
        assert path.read_bytes() == b"archive"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["PENDING", "RUNNING", "ERROR", "CANCELLED", "PAUSED"])
async def test_incomplete_run_refused_in_both_variants(completed, status):
    agent, row = completed
    row["status"] = status
    with pytest.raises(ValueError, match="COMPLETED"):
        async with open_run_checkpoint(agent, row):
            pass
    with pytest.raises(ValueError, match="COMPLETED"):
        with open_run_checkpoint_sync(agent, row):
            pass


@pytest.mark.asyncio
async def test_archive_integrity_is_checked(completed):
    agent, row = completed
    ref = SimpleNamespace(**row["run_data"]["metadata"]["sandbox"]["checkpoint"])
    with agent.sandbox.checkpoints.open_archive(ref) as path:
        path.write_bytes(b"damaged")
    with pytest.raises(Exception, match="digest|size|match"):
        async with open_run_checkpoint(agent, row):
            pass
    with pytest.raises(Exception, match="digest|size|match"):
        with open_run_checkpoint_sync(agent, row):
            pass
