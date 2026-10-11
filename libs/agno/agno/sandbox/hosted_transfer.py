"""Portable bounded checkpoints transported through hosted filesystem APIs."""

import hashlib
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
from uuid import uuid4

from agno.sandbox.base import SandboxError, SandboxHandle, _sync
from agno.sandbox.checkpoint import CheckpointArchive, CheckpointLimits, CheckpointRef, FileCheckpointStore, _thread
from agno.sandbox.hosted import HostedSandboxProvider, _drain
from agno.sandbox.transfer import DEFAULT_NATIVE_EXCLUSIONS


class HostedCheckpointTransfer:
    """Capture managed roots, excluding known native credential files.

    The initial transport buffers at most 64 MiB of archive bytes per operation.
    Capture freezes user processes permanently; callers destroy this computer
    after publishing recovery and restore into a fresh computer for the next turn.
    Quiesce transactional applications before capture when logical consistency is
    required. Mounted external storage and running processes are not checkpointed.
    """

    def __init__(
        self,
        provider: HostedSandboxProvider,
        store: FileCheckpointStore,
        *,
        archive: Optional[CheckpointArchive] = None,
    ) -> None:
        self.provider, self.store = provider, store
        self.archive = archive or CheckpointArchive(CheckpointLimits(max_bytes=64 * 1024 * 1024))
        if self.archive.limits.max_bytes > 64 * 1024 * 1024:
            raise ValueError("Hosted archive transfer currently supports at most 64 MiB")

    async def acapture(
        self, handle: SandboxHandle, *, state: Mapping[str, Any], exclude: Sequence[str] = DEFAULT_NATIVE_EXCLUSIONS
    ) -> CheckpointRef:
        name = uuid4().hex + ".tar"
        metadata = await self.provider._control(
            handle,
            "capture",
            dict(object=name, state=dict(state), exclude=list(exclude), limits=asdict(self.archive.limits)),
        )
        reference = CheckpointRef(**metadata)
        if reference.size > self.archive.limits.max_bytes:
            raise SandboxError("Hosted checkpoint exceeds its transfer limit")
        await self.provider._owned(handle, running=True)
        payload = await _drain(
            self.provider._read(handle.provider_ref, "/var/lib/agno-control/" + name, max_bytes=reference.size)
        )
        if len(payload) != reference.size or hashlib.sha256(payload).hexdigest() != reference.sha256:
            raise SandboxError("Hosted checkpoint download differs from the captured object")
        with tempfile.TemporaryDirectory(prefix=".hosted-capture-", dir=self.store.root) as directory:
            path = Path(directory) / "checkpoint.tar"
            await _thread(path.write_bytes, payload)
            await self.archive.avalidate(path)
            result = await self.store.aput(path)
        await self.provider._control(handle, "remove", {"object": name})
        return result

    def capture(
        self, handle: SandboxHandle, *, state: Mapping[str, Any], exclude: Sequence[str] = DEFAULT_NATIVE_EXCLUSIONS
    ) -> CheckpointRef:
        return _sync(self.acapture(handle, state=state, exclude=exclude))

    async def arestore(self, handle: SandboxHandle, reference: CheckpointRef) -> Mapping[str, Any]:
        if reference.size > self.archive.limits.max_bytes:
            raise SandboxError("Hosted checkpoint exceeds its transfer limit")
        source = await self.store.averify(reference)
        state = await self.archive.avalidate(source)
        payload = await _thread(source.read_bytes)
        name = uuid4().hex + ".tar"
        await self.provider._owned(handle, running=True)
        try:
            await _drain(self.provider._write(handle.provider_ref, "/var/lib/agno-control/" + name, payload))
            response = await self.provider._control(
                handle, "restore", dict(object=name, limits=asdict(self.archive.limits), **asdict(reference))
            )
            if response.get("state") != state:
                raise SandboxError("Hosted restored manifest differs from the verified checkpoint")
            return state
        except BaseException:
            await _drain(self.provider.astop(handle))
            raise

    def restore(self, handle: SandboxHandle, reference: CheckpointRef) -> Mapping[str, Any]:
        return _sync(self.arestore(handle, reference))
