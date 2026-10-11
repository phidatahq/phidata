"""Daytona prepared-snapshot execution with explicit allocation reconciliation."""

import math
import shlex
from contextlib import closing
from typing import Any, Dict, Optional, Sequence

from agno.sandbox.allocation import PostgresAllocationJournal
from agno.sandbox.base import ExecResult, SandboxError, SandboxSpec
from agno.sandbox.checkpoint import _thread
from agno.sandbox.hosted import HostedComputer, HostedSandboxProvider


class DaytonaSandboxProvider(HostedSandboxProvider):
    """Use prepared root-controlled snapshots with a separate unprivileged harness.

    Requires Python 3.10+ and ``agno[daytona-sandbox]``. Snapshot CPU/memory must
    match the requested specification. Idle pause/stop/archive are disabled;
    an absolute lifetime rounded up to minutes bounds abandoned compute.
    """

    backend = "daytona"

    def __init__(
        self,
        namespace: str,
        journal: PostgresAllocationJournal,
        *,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        target: Optional[str] = None,
        max_allocations: int = 10,
        lifetime: int = 1800,
    ) -> None:
        super().__init__(namespace, journal, max_allocations=max_allocations, lifetime=lifetime)
        try:
            from daytona import Daytona, DaytonaConfig
        except ImportError as error:
            raise ImportError("Install agno[daytona-sandbox] with Python 3.10+ to use Daytona sandboxes") from error
        # Polling keeps construction free of background websocket connections;
        # all lifecycle waits remain explicitly bounded by the adapter.
        self._client = Daytona(
            DaytonaConfig(
                api_key=api_key, api_url=api_url, target=target, use_deprecated_polling=True, otel_enabled=False
            )
        )
        # Daytona's toolbox retries RemoteDisconnected for POST. A command may
        # already have executed before that disconnect, so disable it explicitly.
        for client in (self._client._api_client, self._client._toolbox_api_client):
            client.configuration.retries = 0
            client.rest_client.pool_manager.connection_pool_kw["retries"] = 0
            client.rest_client.pool_manager.clear()

    @staticmethod
    def _computer(sandbox: Any) -> HostedComputer:
        metadata = {key[5:]: value for key, value in sandbox.labels.items() if key.startswith("agno_")}
        state = str(sandbox.state.value if hasattr(sandbox.state, "value") else sandbox.state)
        return HostedComputer(
            sandbox.id, metadata, "running" if state == "started" else "dead" if state == "destroyed" else state
        )

    def _sandbox(self, provider_ref: str, *, running: bool = False) -> Any:
        from daytona.common.errors import DaytonaNotFoundError

        try:
            sandbox = self._client.get(provider_ref, request_timeout=30)
        except DaytonaNotFoundError:
            if running:
                raise SandboxError("Daytona computer is missing")
            return None
        if self._computer(sandbox).state == "dead":
            if running:
                raise SandboxError("Daytona computer was destroyed")
            return None
        if running and self._computer(sandbox).state != "running":
            raise SandboxError("Daytona computer is not running; implicit resume is disabled")
        return sandbox

    async def _create(self, spec: SandboxSpec, metadata: Dict[str, str]) -> HostedComputer:
        from daytona import CreateSandboxFromSnapshotParams

        params = CreateSandboxFromSnapshotParams(
            name=metadata["name"],
            snapshot=spec.image,
            os_user="root",
            env_vars=dict(spec.env),
            labels={"agno_" + key: value for key, value in metadata.items()},
            public=False,
            network_block_all=spec.network == "none",
            auto_stop_interval=0,
            auto_pause_interval=0,
            auto_archive_interval=0,
            auto_delete_interval=0,
            ttl_minutes=math.ceil(self.lifetime / 60),
        )
        return await _thread(lambda: self._computer(self._client.create(params, timeout=120)))

    async def _check_resources(self, spec: SandboxSpec, computer: HostedComputer) -> None:
        sandbox = await _thread(self._sandbox, computer.provider_ref, running=True)
        if sandbox.cpu != spec.cpus or sandbox.memory * 1024 != spec.memory_mb:
            raise SandboxError("Daytona snapshot CPU/memory differs from the requested specification")
        if sandbox.network_block_all is not (spec.network == "none"):
            raise SandboxError("Daytona network policy differs from the requested specification")

    async def _get(self, provider_ref: str) -> Optional[HostedComputer]:
        sandbox = await _thread(self._sandbox, provider_ref)
        return None if sandbox is None else self._computer(sandbox)

    async def _inventory(self, token: str) -> Sequence[HostedComputer]:
        from daytona import ListSandboxesQuery

        query = ListSandboxesQuery(labels={"agno_namespace": self.namespace, "agno_token": token})
        return await _thread(
            lambda: [
                self._computer(sandbox)
                for sandbox in self._client.list(query, request_timeout=30)
                if self._computer(sandbox).state != "dead"
            ]
        )

    async def _delete(self, provider_ref: str) -> None:
        def delete() -> None:
            sandbox = self._sandbox(provider_ref)
            if sandbox is not None:
                sandbox.delete(timeout=120, wait=True)

        await _thread(delete)

    async def _command(self, provider_ref: str, argv: Sequence[str], *, timeout: float) -> ExecResult:
        def command() -> ExecResult:
            result = self._sandbox(provider_ref, running=True).process.exec(
                shlex.join(argv), timeout=math.ceil(timeout)
            )
            return ExecResult(
                result.exit_code,
                result.result if result.exit_code == 0 else "",
                result.result if result.exit_code else "",
            )

        return await _thread(command)

    async def _write(self, provider_ref: str, path: str, payload: bytes) -> None:
        await _thread(lambda: self._sandbox(provider_ref, running=True).fs.upload_file(payload, path, timeout=120))

    async def _read(self, provider_ref: str, path: str, *, max_bytes: int) -> bytes:
        def read() -> bytes:
            sandbox = self._sandbox(provider_ref, running=True)
            if sandbox.fs.get_file_info(path, request_timeout=30).size > max_bytes:
                raise SandboxError("Daytona transfer exceeds its byte limit")
            chunks, size = [], 0
            with closing(sandbox.fs.download_file_stream(path, timeout=120)) as stream:
                for chunk in stream:
                    size += len(chunk)
                    if size > max_bytes:
                        raise SandboxError("Daytona transfer exceeds its byte limit")
                    chunks.append(chunk)
            return b"".join(chunks)

        return await _thread(read)
