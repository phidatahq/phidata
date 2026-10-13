"""AgentOS as the host, a Claude turn in a Docker sandbox, the relay inside the host process.

Everything a user touches is on this side: an AgentOS app, Postgres, Redis, and an agent
declared like any other. What runs in the container is Claude Code; what crosses the
boundary is the runtime protocol. This is the shape of the finished SandboxAgent reduced
to what exists on this branch: no checkpoint restore and no lease table yet, so a
session's container is reused warm (paused between turns, resumed on the next) and a
lost container starts a fresh generation.

Where the relay lives: inside this AgentOS process, started by its lifespan. It is not
user-facing. It follows every execution of the provider's namespace and writes events
into the AgentOS event stream, the same Redis-backed stream SSE and /resume read, so a
turn survives the worker that started it. The adapter serves a turn from that stream;
the relay is the only reader of the container.

    docker run -d -p 6379:6379 redis
    ./cookbook/scripts/run_pgvector.sh
    .venv/bin/python cookbook/frameworks/sandbox/build_image.py --tag agno-sandbox:local
    export ANTHROPIC_API_KEY=...             # or CLAUDE_CODE_OAUTH_TOKEN
    .venv/bin/python cookbook/frameworks/sandbox/agentos_sandbox.py

    curl -N -X POST http://localhost:7777/agents/coder/runs \\
      -F message='Create hello.py that prints hello, run it, reply with only the output' \\
      -F session_id=demo -F stream=true
"""

import asyncio
import json
import os
from contextlib import aclosing, asynccontextmanager
from dataclasses import field
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from agno.agents._config import agent_dataclass
from agno.agents.base import BaseExternalAgent, ExternalRunResult
from agno.db.postgres import PostgresDb
from agno.os import AgentOS
from agno.run.agent import RunOutputEvent, run_output_event_from_dict
from agno.sandbox.base import SandboxError, SandboxHandle
from agno.sandbox.client import SandboxRuntimeClient
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.relay import EventStreamRelaySink, RedisRelayState, SandboxRelay

IMAGE = os.environ.get("AGNO_SANDBOX_IMAGE", "agno-sandbox:local")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
)
NAMESPACE = os.environ.get("SANDBOX_NAMESPACE", "agentos-sandbox")


def _event_dict(payload: Any) -> Dict[str, Any]:
    """An event stream replay item as a dict: the in-memory stream hands back event objects,
    the Redis stream hands back the stored SSE text."""
    if hasattr(payload, "to_dict"):
        return payload.to_dict()
    if isinstance(payload, str):
        for line in payload.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:])
        raise SandboxError("Event stream replay item has no data line")
    return dict(payload)


@agent_dataclass
class SandboxedClaude(BaseExternalAgent):
    """Claude Code running in a session-owned Docker container, driven through the runtime protocol."""

    provider: Optional[DockerSandbox] = field(default=None, repr=False)
    runtime_config: Dict[str, Any] = field(default_factory=dict, repr=False)
    env: Dict[str, str] = field(default_factory=dict, repr=False)
    # With relay state, a turn's events are read from the AgentOS event stream, where the relay
    # put them, instead of from the container. Without it, the adapter polls the container itself.
    relay_state: Optional[RedisRelayState] = field(default=None, repr=False)
    _sdk_name = "sandbox"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.provider is None:
            raise ValueError("SandboxedClaude needs a DockerSandbox provider")
        self._client = SandboxRuntimeClient(self.provider)

    async def _computer(self, session: Any, session_id: str) -> SandboxHandle:
        """The session's container: resume it if paused, reuse it if running, else a new generation."""
        assert self.provider is not None
        state = (
            (session.session_data or {}).get("sandbox") if session is not None else None
        )
        generation = int(state["generation"]) if state else 1
        if state:
            current = await self.provider.aget(state["provider_ref"])
            if current is not None and current.state == "paused":
                return await self.provider.aresume(current)
            if current is not None and current.state == "running":
                return current
            generation += (
                1  # gone or stopped: the finished stack restores the checkpoint here
            )
        handle = await self.provider.acreate(
            session_id, agent_id=self.id, generation=generation, env=self.env
        )
        if session is not None:
            session.session_data = {
                **(session.session_data or {}),
                "sandbox": {
                    "provider_ref": handle.provider_ref,
                    "generation": generation,
                },
            }
        return handle

    async def _turn(self, input: Any, kwargs: Dict[str, Any]) -> AsyncIterator[Any]:
        session_id = kwargs.get("session_id") or str(uuid4())
        run_id = kwargs.get("run_id") or str(uuid4())
        computer = await self._computer(kwargs.get("session"), session_id)
        execution = await self._client.astart(
            computer,
            execution_id=run_id,  # retries and redeliveries attach to the same turn
            run_id=run_id,
            sdk="claude",
            input=str(input),
            config=self.runtime_config,
            user_id=kwargs.get("user_id"),
            execution_timeout=600,
        )
        try:
            if self.relay_state is not None:
                async for item in self._from_event_stream(session_id, run_id):
                    yield item
            else:
                async for page in self._client.apages(execution, timeout=600):
                    for event in page.events:
                        yield event
                    if page.result is not None:
                        yield page.result
        finally:
            assert self.provider is not None
            await self.provider.apause(
                computer
            )  # warm: files, memory and processes kept for the next turn

    async def _from_event_stream(
        self, session_id: str, run_id: str
    ) -> AsyncIterator[Any]:
        """Follow the AgentOS event stream for this run, then hand over the relayed result."""
        from agno.os.event_streams import get_event_stream

        assert self.relay_state is not None
        stream = get_event_stream()
        seen = -1
        deadline = asyncio.get_running_loop().time() + 600
        while asyncio.get_running_loop().time() < deadline:
            for index, event in await stream.replay(run_id, last_event_index=seen):
                seen = max(seen, index)
                yield _event_dict(event)
            result = await self.relay_state.aget_result(session_id, run_id)
            if result is not None:
                for index, event in await stream.replay(run_id, last_event_index=seen):
                    seen = max(seen, index)
                    yield _event_dict(event)
                yield result
                return
            await asyncio.sleep(0.2)
        raise SandboxError("Timed out waiting for the relay to deliver the turn")

    async def _arun_adapter_stream(
        self,
        input: Any,
        *,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[RunOutputEvent]:
        # aclosing runs the turn's finally (the pause) before this returns, not at garbage collection.
        async with aclosing(self._turn(input, kwargs)) as turn:
            async for item in turn:
                if "type" in item and str(item["type"]).startswith("execution"):
                    if item["type"] != "execution_finished":
                        raise SandboxError(item.get("error") or item["type"])
                    continue
                if item.get("event") == "RunStarted":
                    continue  # the base class emits the service lifecycle events
                yield run_output_event_from_dict(item)

    async def _arun_adapter(
        self,
        input: Any,
        *,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> ExternalRunResult:
        async with aclosing(self._turn(input, kwargs)) as turn:
            async for item in turn:
                if item.get("type") == "execution_finished":
                    return ExternalRunResult(str(item["run"].get("content") or ""))
                if item.get("type") in ("execution_error", "execution_unknown"):
                    raise SandboxError(item.get("error") or item["type"])
        raise SandboxError("Sandbox turn ended without a result")


provider = DockerSandbox(
    IMAGE, namespace=NAMESPACE, network="bridge", memory_mb=1024, runtime_port=8765
)
credentials = {
    k: os.environ[k]
    for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
    if k in os.environ
}
agent = SandboxedClaude(
    id="coder",
    name="Sandboxed Claude",
    provider=provider,
    env=credentials,
    # Turns are served from the event stream the relay fills; SANDBOX_EVENTS_FROM=container polls directly.
    relay_state=None
    if os.environ.get("SANDBOX_EVENTS_FROM") == "container"
    else RedisRelayState(REDIS_URL),
    runtime_config={
        "model": "claude-sonnet-4-6",
        "permission_mode": "bypassPermissions",
        "allowed_tools": ["Read", "Write", "Bash"],
        "setting_sources": [],
        "max_turns": 12,
    },
)


@asynccontextmanager
async def lifespan(app):
    """The relay runs here, in the host process, for the life of the app.

    The event stream is Redis-backed so every AgentOS process sees the same indexed events:
    SSE, /resume and the adapter all read what the relay wrote.
    """
    import redis.asyncio as aioredis

    from agno.os.event_streams import RedisEventStream, set_event_stream

    set_event_stream(RedisEventStream(aioredis.from_url(REDIS_URL)))
    state = RedisRelayState(REDIS_URL)
    relay = SandboxRelay(provider, EventStreamRelaySink(state), sweep_interval=0.5)
    stop = asyncio.Event()
    task = asyncio.create_task(relay.arun(stop=stop))
    try:
        yield
    finally:
        stop.set()
        await task
        await state.aclose()


agent_os = AgentOS(
    id="sandbox-demo",
    agents=[agent],
    db=PostgresDb(db_url=DATABASE_URL),
    lifespan=lifespan,
    telemetry=False,
)
app = agent_os.get_app()

if __name__ == "__main__":
    print(
        json.dumps(
            {
                "image": IMAGE,
                "namespace": NAMESPACE,
                "redis": REDIS_URL,
                "db": DATABASE_URL.split("@")[-1],
            }
        )
    )
    agent_os.serve(app=app, port=int(os.environ.get("PORT", "7777")), reload=False)
