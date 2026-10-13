"""Model-free diagnostics over an AgentOS: what is configured, and what is live.

Every check is deterministic and free. A check reports whether its evidence is
``configuration`` (the OS object says so) or ``live`` (a read against the
database or the network succeeded). The report never carries secret values:
credential checks say present or absent, and a failing check names the
exception type, not its message.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import time
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Sequence
from uuid import uuid4

if TYPE_CHECKING:
    from agno.os.app import AgentOS

Status = Literal["PASS", "WARN", "FAIL", "SKIP"]
Evidence = Literal["configuration", "live"]

CHECKS: Sequence[str] = ("database", "authorization", "components", "registry", "interfaces", "scheduler", "mcp")

# Worst status wins for the report as a whole.
_SEVERITY = {"FAIL": 3, "WARN": 2, "PASS": 1, "SKIP": 0}


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str
    evidence: Evidence = "configuration"


@dataclass
class DiagnosticReport:
    run_id: str
    created_at: int
    status: Status
    checks: List[CheckResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


async def _call_db(db: Any, method_name: str, *args: Any, **kwargs: Any) -> Any:
    fn = getattr(db, method_name)
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    return await asyncio.to_thread(fn, *args, **kwargs)


async def arun_diagnostics(
    agent_os: "AgentOS",
    *,
    required_env: Sequence[str] = (),
    network_probe: bool = False,
    public_url: Optional[str] = None,
) -> DiagnosticReport:
    """Run every check and return a report.

    Args:
        agent_os: The OS to inspect.
        required_env: Environment variable names whose presence is required. Only
            presence is reported, never the value.
        network_probe: Also POST an MCP initialize to ``public_url`` and report the
            HTTP status. Off by default: it needs the public address and a network.
        public_url: The address the probe targets. Required when ``network_probe`` is on.
    """
    if network_probe and not public_url:
        raise ValueError("network_probe requires public_url")
    checks: List[CheckResult] = []
    for name in CHECKS:
        try:
            checks.append(await _check(agent_os, name, network_probe=network_probe, public_url=public_url))
        except Exception as exc:
            # Driver and provider exceptions can echo credentials; keep the type only.
            checks.append(CheckResult(name=name, status="FAIL", detail=f"Check failed ({type(exc).__name__})"))
    for key in required_env:
        present = bool(os.getenv(key))
        checks.append(
            CheckResult(
                name=f"env:{key}",
                status="PASS" if present else "FAIL",
                detail="Set" if present else "Not set",
            )
        )
    status: Status = max((check.status for check in checks), key=lambda s: _SEVERITY[s], default="SKIP")
    return DiagnosticReport(run_id=str(uuid4()), created_at=int(time.time()), status=status, checks=checks)


def run_diagnostics(
    agent_os: "AgentOS",
    *,
    required_env: Sequence[str] = (),
    network_probe: bool = False,
    public_url: Optional[str] = None,
) -> DiagnosticReport:
    """Sync variant of arun_diagnostics. Inside a running event loop use the async variant."""
    coroutine = arun_diagnostics(
        agent_os, required_env=required_env, network_probe=network_probe, public_url=public_url
    )
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    coroutine.close()
    raise RuntimeError("run_diagnostics was called inside an event loop; await arun_diagnostics instead")


async def _check(agent_os: "AgentOS", name: str, *, network_probe: bool, public_url: Optional[str]) -> CheckResult:
    if name == "database":
        if agent_os.db is None:
            return CheckResult(name, "SKIP", "No OS database configured")
        # One bounded read proves the adapter and the connection without returning user rows.
        await _call_db(agent_os.db, "get_sessions", limit=1, page=1)
        return CheckResult(name, "PASS", "Session read succeeded", evidence="live")

    if name == "authorization":
        if agent_os.authorization:
            return CheckResult(name, "PASS", "Authorization enabled")
        return CheckResult(name, "WARN", "Authorization disabled; every caller is anonymous")

    if name == "components":
        entries = [*(agent_os.agents or []), *(agent_os.teams or []), *(agent_os.workflows or [])]
        ids = [getattr(entry, "id", None) for entry in entries]
        if not all(ids):
            return CheckResult(name, "FAIL", "A registered component has no id")
        if len(ids) != len(set(ids)):
            return CheckResult(name, "FAIL", "Duplicate component ids")
        return CheckResult(name, "PASS", f"{len(entries)} components registered with unique ids")

    if name == "registry":
        registry = agent_os.registry
        if registry is None:
            return CheckResult(name, "SKIP", "No registry")
        knowledge_names = [getattr(k, "name", None) for k in registry.knowledge]
        learning_names = [getattr(m, "name", None) for m in registry.learning]
        if len(knowledge_names) != len(set(knowledge_names)) or len(learning_names) != len(set(learning_names)):
            return CheckResult(name, "FAIL", "Two registry knowledge bases or learning machines share a name")
        return CheckResult(name, "PASS", "Declared knowledge and learning names are unique")

    if name == "interfaces":
        missing = [
            interface
            for interface in agent_os.interfaces
            if getattr(interface, "type", None) == "slack"
            and not (getattr(interface, "token", None) and getattr(interface, "signing_secret", None))
        ]
        if missing:
            return CheckResult(name, "FAIL", "A Slack interface is missing its token or signing secret")
        return CheckResult(name, "PASS", f"{len(agent_os.interfaces)} interfaces configured; delivery not tested")

    if name == "scheduler":
        if not getattr(agent_os, "_scheduler_enabled", False):
            return CheckResult(name, "SKIP", "Scheduler disabled")
        if agent_os.db is None:
            return CheckResult(name, "FAIL", "Scheduler enabled without a database")
        rows = await _call_db(agent_os.db, "get_schedules", enabled=True, limit=100, page=1)
        if isinstance(rows, tuple):
            rows = rows[0]
        now = int(time.time())
        overdue = [
            row
            for row in rows or []
            if (row.get("next_run_at") or now) < now - 900
            and not (row.get("locked_by") and (row.get("locked_at") or 0) > now - 300)
        ]
        if overdue:
            return CheckResult(name, "WARN", f"{len(overdue)} enabled schedules are overdue by 15 minutes", "live")
        return CheckResult(name, "PASS", "No overdue schedules; poller liveness not proven", evidence="live")

    if name == "mcp":
        if not agent_os.mcp:
            return CheckResult(name, "SKIP", "MCP server disabled")
        if not network_probe:
            return CheckResult(name, "PASS", "MCP server configured; endpoint not probed")
        import httpx

        assert public_url is not None
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.post(
                public_url.rstrip("/") + "/mcp",
                headers={"Accept": "application/json, text/event-stream"},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "agno-diagnostics", "version": "1"},
                    },
                },
            )
        if response.status_code == 404:
            return CheckResult(name, "FAIL", "MCP endpoint returned HTTP 404", evidence="live")
        return CheckResult(
            name, "PASS", f"MCP endpoint reachable (HTTP {response.status_code}); tool execution not tested", "live"
        )

    raise ValueError(f"Unknown diagnostic check: {name}")
