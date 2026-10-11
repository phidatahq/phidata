"""Modal sandbox adapter using prepared images and portable file checkpoints."""

import asyncio
import math
from typing import Any, Dict, Optional, Sequence

from agno.sandbox.allocation import PostgresAllocationJournal
from agno.sandbox.base import ExecResult, SandboxError, SandboxSpec
from agno.sandbox.hosted import HostedComputer, HostedSandboxProvider


class ModalSandboxProvider(HostedSandboxProvider):
    """Run prepared Linux images under Modal's gVisor sandbox runtime.

    Requires Python 3.10+ and ``agno[modal-sandbox]``. The named Modal application
    must already exist. Service-side Modal credentials are never injected into
    the image; OIDC identity injection is disabled. No mounted volumes or native
    snapshots are used, so recovery follows the common managed-root contract.
    """

    backend = "modal"

    def __init__(
        self,
        namespace: str,
        journal: PostgresAllocationJournal,
        *,
        app_name: str,
        environment_name: Optional[str] = None,
        max_allocations: int = 10,
        lifetime: int = 1800,
    ) -> None:
        super().__init__(namespace, journal, max_allocations=max_allocations, lifetime=lifetime)
        if not app_name:
            raise ValueError("An existing Modal application name is required")
        try:
            import modal
        except ImportError as error:
            raise ImportError("Install agno[modal-sandbox] with Python 3.10+ to use Modal sandboxes") from error
        self._sdk, self.app_name, self.environment_name = modal, app_name, environment_name

    async def _app(self) -> Any:
        return await self._sdk.App.lookup.aio(
            self.app_name, environment_name=self.environment_name, create_if_missing=False
        )

    async def _sandbox(self, provider_ref: str, *, running: bool = False) -> Any:
        from modal.exception import NotFoundError

        try:
            sandbox = await self._sdk.Sandbox.from_id.aio(provider_ref)
        except NotFoundError:
            if running:
                raise SandboxError("Modal computer is missing")
            return None
        if await sandbox.poll.aio() is not None:
            if running:
                raise SandboxError("Modal computer has terminated")
            return None
        return sandbox

    async def _create(self, spec: SandboxSpec, metadata: Dict[str, str]) -> HostedComputer:
        app = await self._app()
        image = self._sdk.Image.from_registry(spec.image, setup_dockerfile_commands=["USER root"]).entrypoint([])
        sandbox = await self._sdk.Sandbox.create.aio(
            "python",
            "-I",
            "-c",
            "import time; time.sleep(2147483647)",
            app=app,
            name=metadata["name"],
            tags=metadata,
            image=image,
            env=dict(spec.env),
            timeout=self.lifetime,
            workdir="/",
            cpu=(spec.cpus, spec.cpus),
            memory=(spec.memory_mb, spec.memory_mb),
            runtime="gvisor",
            block_network=spec.network == "none",
            include_oidc_identity_token=False,
        )
        return HostedComputer(sandbox.object_id, metadata, "running")

    async def _get(self, provider_ref: str) -> Optional[HostedComputer]:
        sandbox = await self._sandbox(provider_ref)
        return None if sandbox is None else HostedComputer(sandbox.object_id, await sandbox.get_tags.aio(), "running")

    async def _inventory(self, token: str) -> Sequence[HostedComputer]:
        app = await self._app()
        computers = []
        async for sandbox in self._sdk.Sandbox.list.aio(
            app_id=app.app_id, tags={"namespace": self.namespace, "token": token}
        ):
            if await sandbox.poll.aio() is None:
                computers.append(HostedComputer(sandbox.object_id, await sandbox.get_tags.aio(), "running"))
        return computers

    async def _delete(self, provider_ref: str) -> None:
        sandbox = await self._sandbox(provider_ref)
        if sandbox is not None:
            await sandbox.terminate.aio(wait=True)

    async def _command(self, provider_ref: str, argv: Sequence[str], *, timeout: float) -> ExecResult:
        sandbox = await self._sandbox(provider_ref, running=True)
        process = await sandbox.exec.aio(*argv, timeout=math.ceil(timeout), text=True)
        stdout, stderr, code = await asyncio.gather(
            process.stdout.read.aio(), process.stderr.read.aio(), process.wait.aio()
        )
        return ExecResult(code, stdout, stderr)

    async def _write(self, provider_ref: str, path: str, payload: bytes) -> None:
        sandbox = await self._sandbox(provider_ref, running=True)
        await sandbox.filesystem.write_bytes.aio(payload, path)

    async def _read(self, provider_ref: str, path: str, *, max_bytes: int) -> bytes:
        sandbox = await self._sandbox(provider_ref, running=True)
        if (await sandbox.filesystem.stat.aio(path)).size > max_bytes:
            raise SandboxError("Modal transfer exceeds its byte limit")
        # Root-owned immutable transfer objects cannot grow after this stat.
        value = await sandbox.filesystem.read_bytes.aio(path)
        if len(value) > max_bytes:
            raise SandboxError("Modal transfer exceeds its byte limit")
        return value
