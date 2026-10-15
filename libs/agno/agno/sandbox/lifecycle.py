"""Explicit compute retirement and retryable deletion of published recovery data."""

from __future__ import annotations

import asyncio
import tempfile
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4

from agno.exceptions import InputCheckError
from agno.sandbox.artifacts import SandboxSessionNotFound
from agno.sandbox.base import SandboxError
from agno.sandbox.checkpoint import CheckpointArchive, CheckpointObjectNotFound, CheckpointRef
from agno.sandbox.coordinator import SandboxCoordinator
from agno.sandbox.postgres import SandboxLeaseLost, SandboxSessionBusy


class SandboxRecoveryDeleted(InputCheckError, SandboxError, ValueError):
    """The session identity is retired and cannot accept another execution."""


class SandboxLifecycle:
    """Retire compute separately from deleting published workspace/native recovery.

    Recovery deletion keeps conversation history and retires the session identity
    until that history is deleted; a recreated session then starts fresh.
    Unreferenced uploads require a separate storage retention
    policy. It does not erase provider logs, external tool effects or backups.
    """

    def __init__(self, coordinator: SandboxCoordinator) -> None:
        self.coordinator = coordinator
        self.store = coordinator.store

    async def aretire(
        self,
        session_id: str,
        *,
        agent_id: str,
        user_id: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        from sqlalchemy import select

        from agno.run.cancel import acancel_run

        row = await self.store._transaction(
            lambda c: (
                c.execute(
                    select(self.store.bindings).where(
                        self.store._key(session_id),
                        self.store.bindings.c.agent_id == agent_id,
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
            return {"session_id": session_id, "compute_retired": True, "recovery_preserved": True}
        if row["record"]["phase"] in ("deleting", "deleted"):
            raise SandboxRecoveryDeleted("Sandbox recovery is being deleted or was deleted")
        await acancel_run(row["run_id"])
        with suppress(SandboxLeaseLost):
            await self.coordinator._aterminate(
                session_id,
                agent_id=agent_id,
                run_id=row["run_id"],
                user_id=user_id,
                queue_attempt=row["queue_attempt"],
                status="CANCELLED",
                reason="Sandbox computer retired",
                env=env,
            )

        async def confirmed() -> None:
            while True:
                current = await self.store._transaction(
                    lambda c: (
                        c.execute(select(self.store.bindings).where(self.store._key(session_id))).mappings().first()
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
            "session_id": session_id,
            "retired_run_id": row["run_id"],
            "compute_retired": True,
            "recovery_preserved": True,
        }

    def retire(
        self,
        session_id: str,
        *,
        agent_id: str,
        user_id: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        return self.store._sync(self.aretire, session_id, agent_id=agent_id, user_id=user_id, env=env)

    async def _begin_delete(self, agent_id: str, session_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        from sqlalchemy import select, update

        def begin(connection: Any) -> Dict[str, Any]:
            assert self.store.sessions is not None and self.store.runs is not None
            # The store's session -> run -> binding order, so a running turn cannot deadlock with this.
            self.store._hold_session(connection, session_id)
            runs = (
                connection.execute(
                    select(self.store.runs.c.run_data)
                    .where(self.store.runs.c.session_id == session_id)
                    .with_for_update()
                )
                .scalars()
                .all()
            )
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

    async def _owned_object(
        self,
        reference: CheckpointRef,
        identity: Dict[str, Any],
        claimed: List[str],
        witness: Optional[Dict[str, Any]],
    ) -> bool:
        """True when the object is present and owned; False when this cleanup already deleted it."""
        objects = self.coordinator.transfer.store
        try:
            async with objects.aopen_archive(reference) as source:
                binding = (await CheckpointArchive().avalidate(source)).get("binding") or {}
        except CheckpointObjectNotFound:
            # Missing proves deletion only for a claimed object while its storage still holds the witness.
            if reference.sha256 in claimed and witness is not None:
                await objects.averify(CheckpointRef(**witness))
                return False
            raise
        if any(binding.get(key) != value for key, value in identity.items()):
            raise SandboxError("Refusing to delete another session's checkpoint")
        return True

    async def _write_witness(self) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "witness"
            source.write_text("agno-recovery-deletion-witness " + uuid4().hex)
            return asdict(await self.coordinator.transfer.store.aput(source))

    async def _claim_object(self, session_id: str, incarnation: Any, sha256: str, witness: Dict[str, Any]) -> None:
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

        # A deleted session still runs finish() so a retry reconciles run/session copies and the witness.
        record = await self._begin_delete(agent_id, session_id, user_id)
        identity = dict(agent_id=agent_id, session_id=session_id, user_id=user_id, incarnation=record["incarnation"])
        objects = self.coordinator.transfer.store
        claimed = list(record.get("claimed_references", []))
        witness = record.get("deletion_witness")
        for value in record["deletion_references"]:
            reference = CheckpointRef(**value)
            if not await self._owned_object(reference, identity, claimed, witness):
                continue
            if reference.sha256 not in claimed:
                witness = witness or await self._write_witness()
                # Both readable after the witness exists, so a retry can trust the witness for this object.
                await objects.averify(CheckpointRef(**witness))
                await objects.averify(reference)
                await self._claim_object(session_id, record["incarnation"], reference.sha256, witness)
            await objects.adelete(reference)

        def finish(connection: Any) -> None:
            assert self.store.runs is not None and self.store.sessions is not None
            # Session, then runs, then binding: the store's order, since this rewrites all three.
            session = (
                connection.execute(
                    select(self.store.sessions).where(self.store.sessions.c.session_id == session_id).with_for_update()
                )
                .mappings()
                .first()
            )
            runs = (
                connection.execute(
                    select(self.store.runs).where(self.store.runs.c.session_id == session_id).with_for_update()
                )
                .mappings()
                .all()
            )
            row = (
                connection.execute(select(self.store.bindings).where(self.store._key(session_id)).with_for_update())
                .mappings()
                .one()
            )
            current = self.store._json(row["record"])
            if current["incarnation"] != record["incarnation"] or current["phase"] not in ("deleting", "deleted"):
                raise SandboxError("Recovery deletion lost its session tombstone")
            if session is not None and "sandbox" in (session["session_data"] or {}):
                data = dict(session["session_data"])
                data.pop("sandbox", None)
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
            with suppress(OSError, SandboxError):
                await objects.adelete(CheckpointRef(**witness))
        return {"session_id": session_id, "recovery_deleted": True, "conversation_retained": True}

    def delete_recovery(self, *, agent_id: str, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        return self.store._sync(self.adelete_recovery, agent_id=agent_id, session_id=session_id, user_id=user_id)
