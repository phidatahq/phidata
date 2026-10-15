"""Company Task execution using the platform's ordinary run and queue contracts."""

import asyncio
import json
from contextvars import ContextVar
from typing import Any, Dict, Optional
from uuid import uuid4

from agno.db.base import AsyncBaseDb
from agno.registry._reserved import RESERVED_MEMBER_IDS
from agno.run.authorization import RunAuthorization

# Trusted, request-local handoff to the existing run routes. It never comes from
# a request field, tool argument, session state or run metadata.
_task_submission: ContextVar[Optional[Dict[str, Any]]] = ContextVar("company_task_submission", default=None)


def _executor(registry: Any, executor_type: Optional[str], executor_id: Optional[str], accepting: bool = False) -> Any:
    if executor_type == "engineering":
        if accepting:
            return None
        raise ValueError("Engineering executors cannot be started yet")
    if executor_type not in {"agent", "team", "workflow"} or executor_id in RESERVED_MEMBER_IDS:
        raise ValueError("Select a registered agent, team or workflow executor")
    component = getattr(registry, "get_" + executor_type)(executor_id) if registry is not None else None
    if component is None:
        raise ValueError("Task executor is missing from the registry")
    if not accepting:
        from agno.agent import RemoteAgent
        from agno.team import RemoteTeam
        from agno.workflow import RemoteWorkflow

        if isinstance(component, (RemoteAgent, RemoteTeam, RemoteWorkflow)):
            raise ValueError("Task execution requires a local executor supported by the durable queue")
    _validate_executor_tools(component)
    return component


async def _call(db: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    fn = getattr(db, method)
    if isinstance(db, AsyncBaseDb):
        return await fn(*args, **kwargs)
    return await asyncio.to_thread(fn, *args, **kwargs)


def _queued_run_id() -> str:
    submission = _task_submission.get()
    return submission["task"]["job_id"] if submission else str(uuid4())


async def _stamp_ticket(job: Dict[str, Any]) -> Dict[str, Any]:
    submission = _task_submission.get()
    if submission is None:
        return job
    task = submission["task"]
    current = await _call(submission["db"], "get_task", task["id"])
    if current is None or current["job_id"] != job["id"] or current["transitions"] != task["transitions"]:
        raise ValueError("Task acceptance changed before submission")
    return {
        **job,
        "payload": {**job["payload"], "company_task_id": task["id"], "company_task_transitions": task["transitions"]},
    }


async def _check_task(worker: Any, job: Dict[str, Any]) -> None:
    task_id = (job.get("payload") or {}).get("company_task_id")
    if not task_id:
        return
    db = getattr(worker, "_company_db", None)
    if db is None:
        raise ValueError("Company is unavailable for this queued Task")
    task = await _call(db, "get_task", task_id)
    if (
        task is None
        or task["job_id"] != job["id"]
        or task["status"] != "in_progress"
        or task["executor_id"] != job["component_id"]
        or task["executor_type"] != job["component_type"]
        or task["transitions"] != job["payload"].get("company_task_transitions")
    ):
        from agno.exceptions import InputCheckError

        raise InputCheckError("Task acceptance was changed or revoked")
    from agno.run.authorization import current_authorization

    authority = current_authorization()
    if authority is not None:
        await authority.arequire(
            {"agent": "agents", "team": "teams", "workflow": "workflows"}[job["component_type"]],
            "run",
            job["component_id"],
        )
    component = await worker._aresolve_job_component(job)
    _validate_executor_tools(component)


async def _project_run(worker: Any, job: Dict[str, Any], status: str, error: Optional[str] = None) -> None:
    task_id = (job.get("payload") or {}).get("company_task_id")
    if not task_id or status not in {"completed", "failed"}:
        return
    db = getattr(worker, "_company_db", None)
    if db is None:
        raise ValueError("Company is unavailable for this queued Task")
    result: Dict[str, Any] = {"run_id": job["id"], "status": "ERROR", "content": error}
    if status == "completed":
        component = await worker._aresolve_job_component(job)
        if component is None:
            raise ValueError("Task executor is unavailable while saving results")
        output = await component.aget_run_output(job["id"], job["session_id"], user_id=job.get("user_id"))
        if output is None or str(getattr(output.status, "value", output.status)) != "COMPLETED":
            raise ValueError("Completed Task run is not durably readable")
        data = output.to_dict()
        result = {key: data.get(key) for key in ("run_id", "status", "content", "content_type")}
    await _call(
        db,
        "complete_task_run",
        task_id,
        job["id"],
        result,
        expected_transitions=job["payload"].get("company_task_transitions"),
    )


async def _task_input(manager: Any, task: Dict[str, Any]) -> str:
    async def call(method: str, *args: Any, **kwargs: Any) -> Any:
        from agno.company.manager import AsyncCompanyManager

        fn = getattr(manager, method)
        return (
            await fn(*args, **kwargs)
            if isinstance(manager, AsyncCompanyManager)
            else await asyncio.to_thread(fn, *args, **kwargs)
        )

    pages = []
    # Both namespaces have company-wide read visibility. No Source credentials,
    # Product metadata, other Tasks or caller-supplied runtime state are forwarded.
    for product_id in (None, task["product_id"]):
        page = 1
        while True:
            rows, total = await call("list_wiki", product_id, limit=100, page=page)
            for row in rows:
                value = await call("read_wiki", product_id, row.path)
                pages.append(
                    {
                        "namespace": "company" if product_id is None else "product",
                        "path": row.path,
                        "content": value.content,
                    }
                )
            if page * 100 >= total:
                break
            page += 1
    return json.dumps(
        {"brief": task.get("brief"), "wiki": pages, "evidence": task.get("evidence") or []}, ensure_ascii=False
    )


def _validate_executor_tools(component: Any) -> None:
    from agno.tools.scheduler import SchedulerTools

    pending = [component]
    seen = set()
    while pending:
        item = pending.pop()
        if item is None or id(item) in seen:
            continue
        seen.add(id(item))
        for tool in getattr(item, "tools", None) or []:
            if isinstance(tool, SchedulerTools) or isinstance(getattr(tool, "__self__", None), SchedulerTools):
                raise ValueError("Company executors cannot hold SchedulerTools")
        for name in ("members", "steps"):
            children = getattr(item, name, None)
            if isinstance(children, (list, tuple)):
                pending.extend(children)
        for name in ("agent", "team", "executor"):
            child = getattr(item, name, None)
            if child is not None:
                pending.append(child)


class _ExecutorAuthorization(RunAuthorization):
    """Attenuate the caller's authority for Company execution and its delegation."""

    def __init__(self, original: Optional[RunAuthorization]):
        from agno.os.auth import _default_authorization_provider
        from agno.os.authz.provider import AuthorizationContext

        self.original = original
        super().__init__(
            original.provider if original else _default_authorization_provider(),
            original.context if original else AuthorizationContext(),
            service_account=original.service_account if original else False,
            enforce_tools=True,
        )

    def require(self, resource: str, action: str, resource_id: Optional[str] = None) -> None:
        if resource == "schedules" and action != "read":
            raise PermissionError("Company executors cannot change schedules")
        if self.original is not None:
            self.original.require(resource, action, resource_id)

    async def arequire(self, resource: str, action: str, resource_id: Optional[str] = None) -> None:
        if resource == "schedules" and action != "read":
            raise PermissionError("Company executors cannot change schedules")
        if self.original is not None:
            await self.original.arequire(resource, action, resource_id)

    def snapshot(self) -> Dict[str, Any]:
        return {**super().snapshot(), "company_executor": True}


def _mount_executors(os: Any) -> None:
    """Expose registry executors through the normal routes when Company is enabled."""
    if os.registry is None:
        return
    for resource in ("agents", "teams", "workflows"):
        served = list(getattr(os, resource) or [])
        by_id = {getattr(component, "id", None): component for component in served}
        for component in getattr(os.registry, resource):
            component_id = getattr(component, "id", None)
            if component_id in RESERVED_MEMBER_IDS:
                continue
            if component_id in by_id:
                if by_id[component_id] is not component:
                    raise ValueError("Company requires one executor per registered type and id")
            else:
                served.append(component)
        setattr(os, resource, served)
