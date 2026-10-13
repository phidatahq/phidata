"""Explicit compute retirement and retryable deletion of published recovery data."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agno.exceptions import InputCheckError
from agno.sandbox.artifacts import SandboxSessionNotFound
from agno.sandbox.base import SandboxError, SandboxSpec
from agno.sandbox.checkpoint import CheckpointArchive, CheckpointRef, _fsync_directory, _thread
from agno.sandbox.coordinator import SandboxCoordinator
from agno.sandbox.postgres import SandboxLeaseLost, SandboxSessionBusy


class SandboxRecoveryDeleted(InputCheckError, SandboxError, ValueError):
    """The session identity is retired and cannot accept another execution."""


class SandboxLifecycle:
    """Retire compute separately from deleting published workspace/native recovery.

    Recovery deletion keeps conversation history and permanently retires the
    session identity. Unreferenced uploads require a separate storage retention
    policy. It does not erase provider logs, external tool effects or backups.
    """

    def __init__(self, coordinator: SandboxCoordinator) -> None:
        self.coordinator = coordinator
        self.store = coordinator.store

    async def aretire(self, spec: SandboxSpec, *, user_id: Optional[str] = None) -> Dict[str, Any]:
        from sqlalchemy import select

        from agno.run.cancel import acancel_run

        row = await self.store._transaction(
            lambda c: (
                c.execute(
                    select(self.store.bindings).where(
                        self.store._key(spec.session_id),
                        self.store.bindings.c.agent_id == spec.agent_id,
                        self.store.bindings.c.user_id == user_id,
                    )
                )
                .mappings()
                .first()
            )
        )
        if row is None:
            raise SandboxSessionNotFound("Sandbox session not found")
        if row["record"]["phase"] == "idle":
            return {"session_id": spec.session_id, "compute_retired": True, "recovery_preserved": True}
        if row["record"]["phase"] in ("deleting", "deleted"):
            raise SandboxRecoveryDeleted("Sandbox recovery is being deleted or was deleted")
        await acancel_run(row["run_id"])
        with suppress(SandboxLeaseLost):
            await self.coordinator._aterminate(
                spec,
                run_id=row["run_id"],
                user_id=user_id,
                queue_attempt=row["queue_attempt"],
                status="CANCELLED",
                reason="Sandbox computer retired",
            )

        async def confirmed() -> None:
            while True:
                current = await self.store._transaction(
                    lambda c: (
                        c.execute(select(self.store.bindings).where(self.store._key(spec.session_id)))
                        .mappings()
                        .first()
                    )
                )
                if current is None or current["record"]["incarnation"] != row["record"]["incarnation"]:
                    raise SandboxError("Session changed before retirement was confirmed")
                if current["run_id"] != row["run_id"] or (
                    current["record"]["phase"] == "idle" and current["record"].get("computer") is None
                ):
                    return
                await asyncio.sleep(0.05)

        try:
            await asyncio.wait_for(confirmed(), 30)
        except asyncio.TimeoutError as error:
            raise SandboxError("Computer retirement is still pending; retry reconciliation") from error
        return {
            "session_id": spec.session_id,
            "retired_run_id": row["run_id"],
            "compute_retired": True,
            "recovery_preserved": True,
        }

    def retire(self, spec: SandboxSpec, *, user_id: Optional[str] = None) -> Dict[str, Any]:
        return self.store._sync(self.aretire, spec, user_id=user_id)

    async def _begin_delete(self, agent_id: str, session_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        from sqlalchemy import select, update

        def begin(connection: Any) -> Dict[str, Any]:
            assert self.store.sessions is not None and self.store.runs is not None
            row = (
                connection.execute(select(self.store.bindings).where(self.store._key(session_id)).with_for_update())
                .mappings()
                .first()
            )
            if row is None or row["agent_id"] != agent_id or row["user_id"] != user_id:
                raise SandboxSessionNotFound("Sandbox session not found")
            record = self.store._json(row["record"])
            if record["phase"] in ("deleting", "deleted"):
                return record
            if record["phase"] != "idle" or record.get("computer") is not None:
                raise SandboxSessionBusy(row["run_id"] or "")
            runs = (
                connection.execute(
                    select(self.store.runs.c.run_data)
                    .where(self.store.runs.c.session_id == session_id)
                    .with_for_update()
                )
                .scalars()
                .all()
            )
            session = (
                connection.execute(
                    select(self.store.sessions).where(self.store.sessions.c.session_id == session_id).with_for_update()
                )
                .mappings()
                .first()
            )
            if session is None or (session["session_data"] or {}).get("_sandbox_incarnation") != record["incarnation"]:
                raise SandboxSessionNotFound("Sandbox session incarnation changed")
            references = {}
            for value in [
                record.get("checkpoint"),
                *record.get("published_checkpoints", []),
                *[((run.get("metadata") or {}).get("sandbox") or {}).get("checkpoint") for run in runs],
            ]:
                if value:
                    reference = CheckpointRef(**value)
                    references[reference.sha256] = value
            record.update(phase="deleting", deletion_references=list(references.values()))
            connection.execute(
                update(self.store.bindings)
                .where(self.store._key(session_id))
                .values(
                    record=record, epoch=row["epoch"] + 1, owner=None, run_id=None, queue_attempt=None, expires_at=None
                )
            )
            return record

        return await self.store._transaction(begin)

    def _owned_object(
        self, reference: CheckpointRef, identity: Dict[str, Any], claimed: List[str], witness: Optional[str]
    ) -> Optional[Path]:
        objects = self.coordinator.transfer.store
        try:
            path = objects.verify(reference)
        except FileNotFoundError:
            # Missing proves deletion only for a claimed object while its volume's witness file is still present.
            if reference.sha256 in claimed and witness is not None and (objects.root / witness).is_file():
                return None
            raise
        binding = CheckpointArchive().validate(path).get("binding") or {}
        if any(binding.get(key) != value for key, value in identity.items()):
            raise SandboxError("Refusing to delete another session's checkpoint")
        return path

    def _write_witness(self, witness: str, path: Path) -> None:
        root = self.coordinator.transfer.store.root
        (root / witness).touch(exist_ok=True)
        _fsync_directory(root)
        if (root / witness).stat().st_dev != path.stat().st_dev:
            raise SandboxError("Checkpoint storage changed during recovery deletion")

    def _remove_object(self, path: Path) -> None:
        path.unlink()
        _fsync_directory(path.parent)

    async def _claim_object(self, session_id: str, incarnation: Any, sha256: str, witness: str) -> None:
        from sqlalchemy import select, update

        def claim(connection: Any) -> None:
            row = (
                connection.execute(select(self.store.bindings).where(self.store._key(session_id)).with_for_update())
                .mappings()
                .one()
            )
            record = self.store._json(row["record"])
            if record["incarnation"] != incarnation or record["phase"] != "deleting":
                raise SandboxError("Recovery deletion lost its session tombstone")
            if record.setdefault("deletion_witness", witness) != witness:
                raise SandboxError("Recovery deletion witness changed")
            claimed = record.setdefault("claimed_references", [])
            if sha256 not in claimed:
                claimed.append(sha256)
            connection.execute(update(self.store.bindings).where(self.store._key(session_id)).values(record=record))

        await self.store._transaction(claim)

    async def adelete_recovery(
        self, *, agent_id: str, session_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        from sqlalchemy import select, update

        # A deleted session still runs finish() so a retry restores a marker lost to a stale session write.
        record = await self._begin_delete(agent_id, session_id, user_id)
        identity = dict(agent_id=agent_id, session_id=session_id, user_id=user_id, incarnation=record["incarnation"])
        claimed = list(record.get("claimed_references", []))
        witness = record.get("deletion_witness")
        for value in record["deletion_references"]:
            reference = CheckpointRef(**value)
            path = await _thread(self._owned_object, reference, identity, claimed, witness)
            if path is None:
                continue
            if reference.sha256 not in claimed:
                witness = witness or ".recovery-delete-" + uuid4().hex
                await _thread(self._write_witness, witness, path)
                await self._claim_object(session_id, record["incarnation"], reference.sha256, witness)
            await _thread(self._remove_object, path)

        def finish(connection: Any) -> None:
            assert self.store.runs is not None and self.store.sessions is not None
            row = (
                connection.execute(select(self.store.bindings).where(self.store._key(session_id)).with_for_update())
                .mappings()
                .one()
            )
            current = self.store._json(row["record"])
            if current["incarnation"] != record["incarnation"] or current["phase"] not in ("deleting", "deleted"):
                raise SandboxError("Recovery deletion lost its session tombstone")
            runs = (
                connection.execute(
                    select(self.store.runs).where(self.store.runs.c.session_id == session_id).with_for_update()
                )
                .mappings()
                .all()
            )
            session = (
                connection.execute(
                    select(self.store.sessions).where(self.store.sessions.c.session_id == session_id).with_for_update()
                )
                .mappings()
                .first()
            )
            if session is not None:
                data = dict(session["session_data"] or {})
                if data.get("_sandbox_incarnation") != record["incarnation"]:
                    raise SandboxError("Session changed during recovery deletion")
                data.pop("sandbox", None)
                data["_sandbox_recovery_deleted"] = record["incarnation"]
                connection.execute(
                    update(self.store.sessions)
                    .where(self.store.sessions.c.session_id == session_id)
                    .values(session_data=data)
                )
            for run in runs:
                data = dict(run["run_data"])
                metadata = dict(data.get("metadata") or {})
                native = dict(metadata.get("sandbox") or {})
                native.pop("checkpoint", None)
                native.pop("native_metadata", None)
                native["recovery_deleted"] = True
                metadata["sandbox"] = native
                data["metadata"] = metadata
                connection.execute(
                    update(self.store.runs).where(self.store.runs.c.run_id == run["run_id"]).values(run_data=data)
                )
            current.update(
                phase="deleted",
                checkpoint=None,
                checkpoint_identity=None,
                staged_checkpoint=None,
                staged_identity=None,
                result=None,
                deletion_references=[],
                claimed_references=[],
                published_checkpoints=[],
            )
            connection.execute(update(self.store.bindings).where(self.store._key(session_id)).values(record=current))

        await self.store._transaction(finish)
        if witness is not None:
            with suppress(FileNotFoundError):
                (self.coordinator.transfer.store.root / witness).unlink()
        return {"session_id": session_id, "recovery_deleted": True, "conversation_retained": True}

    def delete_recovery(self, *, agent_id: str, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        return self.store._sync(self.adelete_recovery, agent_id=agent_id, session_id=session_id, user_id=user_id)
