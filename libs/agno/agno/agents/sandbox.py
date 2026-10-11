"""AgentOS-compatible coding agents whose harness executes in a session computer."""

from __future__ import annotations

import json
from dataclasses import field
from typing import Any, AsyncIterator, ClassVar, Dict, Literal, Optional
from uuid import uuid4

from agno.agents._config import agent_dataclass
from agno.agents.base import BaseExternalAgent
from agno.run.agent import RunInput, RunOutput
from agno.run.base import RunStatus
from agno.sandbox import SandboxError, SandboxSpec
from agno.sandbox.coordinator import SandboxCoordinator


@agent_dataclass
class SandboxAgent(BaseExternalAgent):
    """Run Claude or Codex in replaceable compute with durable managed files.

    Call coordinator.store.setup/asetup before accepting traffic. AgentOS API
    execution requires a durable QueueConfig; every response mode submits there.
    Direct Python run/arun uses the same Postgres session fence. SDK background
    submission requires an active AgentOS queue. Native options are JSON and
    provisioned consistently across replicas. File/image bytes are bounded and
    checkpointed inside compute. Step replay requires a separate recovery API.
    """

    coordinator: Optional[SandboxCoordinator] = field(default=None, repr=False)
    image: Optional[str] = None
    harness: Literal["claude", "codex", "fixture"] = "claude"
    runtime_config: Dict[str, Any] = field(default_factory=dict, repr=False)
    env: Dict[str, str] = field(default_factory=dict, repr=False)
    network: str = "none"
    cpus: float = 2
    memory_mb: int = 2048
    workspace_mb: int = 512
    pids_limit: int = 256
    execution_timeout: float = 900

    _sdk_name: ClassVar[str] = "sandbox"
    _sandbox_execution: ClassVar[bool] = True
    _supports_output_schema: ClassVar[bool] = True

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.coordinator is None or not self.image:
            raise ValueError("SandboxAgent requires a coordinator and runtime image")
        if self.db is not None and self.db is not self.coordinator.store.db:
            raise ValueError("SandboxAgent must use the coordinator's service database")
        self.db = self.coordinator.store.db
        if self.retries:
            raise ValueError("Configure sandbox execution retries on QueueConfig, not the agent")
        if self.harness == "fixture" and self.env.get("AGNO_SANDBOX_TEST_RUNTIME") != "1":
            raise ValueError("The fixture harness requires explicit test-runtime opt-in")
        self.runtime_config = json.loads(json.dumps(self.runtime_config, allow_nan=False))
        self.env = dict(self.env)
        self._spec("validate")
        self._submission("validate", {})

    def _spec(self, session_id: str) -> SandboxSpec:
        return SandboxSpec(
            self.get_id(),
            session_id,
            1,
            self.image or "",
            env=self.env,
            network=self.network,
            cpus=self.cpus,
            memory_mb=self.memory_mb,
            workspace_mb=self.workspace_mb,
            pids_limit=self.pids_limit,
        )

    def _media_kwargs(self, **media: Any) -> Dict[str, Any]:
        from agno.sandbox.media import encode_media

        wire = encode_media(media, allow_local_paths=True)
        return {"sandbox_media": wire} if wire else {}

    def _submission(self, input: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        from agno.sandbox.protocol import validate_request

        if not isinstance(input, str):
            raise ValueError("SandboxAgent input must be text")
        extra = {key: value for key, value in kwargs.items() if value is not None}
        for key in ("run_id", "session_id", "user_id", "yield_run_output", "stream_events", "background_tasks"):
            extra.pop(key, None)
        unknown = set(extra) - {"output_schema", "sandbox_media"}
        if unknown:
            raise ValueError("Unsupported sandbox run options: " + ", ".join(sorted(unknown)))
        schema = extra.get("output_schema", self.output_schema)
        self._check_output_schema(schema)
        if schema is not None and not isinstance(schema, dict):
            schema = schema.model_json_schema()
        config = json.loads(json.dumps(self.runtime_config, allow_nan=False))
        if schema is not None:
            config["output_schema"] = schema
        if self.name is not None:
            config["name"] = self.name
        validate_request(
            dict(
                version=1,
                execution_id="validate",
                run_id="validate",
                agent_id=self.get_id(),
                session_id="validate",
                sdk="claude" if self.harness == "fixture" else self.harness,
                input=input,
                media=extra.get("sandbox_media", []),
                config=config,
                execution_timeout=self.execution_timeout,
            )
        )
        result = {"output_schema": schema} if schema is not None else {}
        if extra.get("sandbox_media"):
            result["sandbox_media"] = json.loads(json.dumps(extra["sandbox_media"]))
        return result

    def _execution(self, input: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        from agno.run.concurrency import get_worker_ownership

        options = self._submission(input, kwargs)
        config = json.loads(json.dumps(self.runtime_config, allow_nan=False))
        media = options.pop("sandbox_media", [])
        config.update(options)
        if self.name is not None:
            config["name"] = self.name
        run_id = kwargs.get("run_id") or str(uuid4())
        owner = get_worker_ownership(run_id)
        return dict(
            run_id=run_id,
            input=input,
            sdk=self.harness,
            media=media,
            user_id=kwargs.get("user_id"),
            config=config,
            queue_attempt=owner.attempt if owner is not None else None,
            execution_timeout=self.execution_timeout,
        )

    async def _arun_non_stream(self, input: Any, **kwargs: Any) -> RunOutput:
        from agno.run.cancel import aregister_run

        assert self.coordinator is not None
        execution = self._execution(input, kwargs)
        await aregister_run(execution["run_id"])
        return await self.coordinator.arun(self._spec(kwargs.get("session_id") or str(uuid4())), **execution)

    async def _arun_stream(self, input: Any, **kwargs: Any) -> AsyncIterator[Any]:
        from agno.run.cancel import aregister_run

        assert self.coordinator is not None
        execution = self._execution(input, kwargs)
        await aregister_run(execution["run_id"])
        iterator = self.coordinator._astream(self._spec(kwargs.get("session_id") or str(uuid4())), **execution)
        events: list[Dict[str, Any]] = []
        skipped = {event.value for event in self.events_to_skip or []}
        try:
            async for value in iterator:
                if isinstance(value, RunOutput) and self.store_events:
                    await self.coordinator.store._apublish_events(value.to_dict(), events)
                if not isinstance(value, RunOutput) or kwargs.get("yield_run_output", False):
                    yield value
                # The queue publisher stamps the same object before resuming us.
                if self.store_events and not isinstance(value, RunOutput) and value.event not in skipped:
                    events.append(value.to_dict())
        finally:
            await iterator.aclose()

    async def _aprepare_pending_run(
        self, run_id: str, session_id: str, user_id: Optional[str], input: Any
    ) -> RunOutput:
        return await self._aprepare_queued_submission(run_id, session_id, user_id, input, {})

    async def _aprepare_queued_submission(
        self, run_id: str, session_id: str, user_id: Optional[str], input: Any, run_kwargs: Dict[str, Any]
    ) -> RunOutput:
        from agno.sandbox.media import decode_media

        assert self.coordinator is not None
        options = self._submission(input, run_kwargs)
        run = RunOutput(
            run_id=run_id,
            session_id=session_id,
            agent_id=self.get_id(),
            user_id=user_id,
            agent_name=self.name,
            input=RunInput(input_content=input, **decode_media(options.get("sandbox_media", []))),
            status=RunStatus.pending,
        )
        await self.coordinator.store.aprepare(run.to_dict())
        return run

    async def _apersist_run_fallback(
        self, session_id: str, run_response: RunOutput, user_id: Optional[str] = None
    ) -> None:
        raise SandboxError("Sandbox execution requires atomic service persistence; unfenced fallback is disabled")

    async def _acancel_unowned_row(self, run_id: str) -> None:
        from contextlib import suppress

        from sqlalchemy import select

        from agno.sandbox.postgres import SandboxLeaseLost

        assert self.coordinator is not None
        store = self.coordinator.store
        row = await store._transaction(
            lambda connection: (
                connection.execute(
                    select(store.bindings).where(
                        store.bindings.c.namespace == store.namespace,
                        store.bindings.c.agent_id == self.get_id(),
                        store.bindings.c.run_id == run_id,
                    )
                )
                .mappings()
                .first()
            )
        )
        if row is not None:
            # Explicit cancel may retire a detached coordinator too. The shared
            # intent remains authoritative if another cancellation wins this race.
            with suppress(SandboxLeaseLost):
                await self.coordinator._aterminate(
                    self._spec(row["session_id"]),
                    run_id=run_id,
                    user_id=row["user_id"],
                    queue_attempt=row["queue_attempt"],
                    status="CANCELLED",
                    reason="Run cancelled",
                )

    async def _apersist_queue_terminal(
        self, job: Dict[str, Any], error: str, status: str, cancellation_stage: Any
    ) -> Any:
        assert self.coordinator is not None
        return await self.coordinator._aterminate(
            self._spec(job["session_id"]),
            run_id=job["id"],
            user_id=job.get("user_id"),
            queue_attempt=job.get("attempt"),
            status="CANCELLED" if status == "cancelled" else "ERROR",
            reason=error[:8192],
        )

    async def _astart_background(
        self,
        input: Any,
        *,
        run_id: str,
        session_id: str,
        user_id: Optional[str],
        stream: bool,
        yield_run_output: bool,
        **kwargs: Any,
    ) -> Any:
        from agno.os.job_queue import get_active_queue_worker
        from agno.os.routers.agents.sandbox import enqueue_sandbox_run

        worker = get_active_queue_worker()
        if worker is None or worker.resolve_component("agent", self.get_id()) is not self:
            raise ValueError("Sandbox background execution requires this agent's active AgentOS durable queue")
        job = await enqueue_sandbox_run(
            self, worker, input=input, session_id=session_id, user_id=user_id, kwargs=kwargs, run_id=run_id
        )
        return RunOutput(
            run_id=job["id"],
            session_id=job["session_id"],
            agent_id=self.get_id(),
            user_id=user_id,
            status=RunStatus.pending,
        )

    async def _arun_background_stream(self, input: Any, **kwargs: Any) -> AsyncIterator[Any]:
        from agno.os.utils import queued_run_tail_streamer

        run = await self._astart_background(input, stream=True, **kwargs)
        async for event in queued_run_tail_streamer(run.run_id):
            yield event
        if kwargs.get("yield_run_output"):
            stored = await self.aget_run_output(run.run_id, run.session_id, user_id=run.user_id)
            if stored is not None:
                yield stored
