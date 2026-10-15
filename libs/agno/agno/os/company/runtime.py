"""Connect Company Tasks to the existing durable AgentOS queue and scheduler."""

import asyncio
import hashlib
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import NAMESPACE_URL, uuid4, uuid5

from agno.os.auth import resolve_authorization_provider
from agno.os.authz.provider import AuthorizationContext
from agno.os.company.context import CompanyContext, current_company
from agno.os.company.policy import CompanyError, Principal
from agno.os.company.service import _json, _query, _row


class CompanyRuntime:
    def __init__(self, service: Any, agent_os: Any):
        self.service, self.os = service, agent_os
        self.worker: Any = None
        self.app: Any = None

    def _principal(self, saved: Dict[str, Any]) -> Principal:
        return Principal(saved["id"], resolve_authorization_provider(self.app), tuple(saved["scopes"]), saved["claims"])

    def _saved(self, principal: Principal) -> Dict[str, Any]:
        # Store the verified authorization inputs, never the bearer credential.
        return {"id": principal.id, "scopes": list(principal.scopes), "claims": dict(principal.claims)}

    def _agent(self, principal: Principal, agent_id: Optional[str]) -> Any:
        from agno.agent import Agent
        from agno.agents.claude import ClaudeAgent
        from agno.agents.codex import CodexAgent

        agent = next((a for a in self.os.agents or [] if a.id == agent_id), None)
        if agent is None or not isinstance(agent, (Agent, CodexAgent, ClaudeAgent)) or agent.db is None:
            raise CompanyError(
                409, "worker_required", "Select a registered Agent, CodexAgent or ClaudeAgent with persistent storage"
            )
        sandbox = getattr(agent, "sandbox", None)
        if isinstance(agent, (CodexAgent, ClaudeAgent)) and (sandbox is None or isinstance(sandbox, str)):
            from pathlib import Path

            if not agent.cwd or not Path(agent.cwd).is_dir():
                raise CompanyError(
                    409, "workspace_required", "Configure an explicit workspace for the Product Engineer"
                )
        if getattr(agent, "_registry_excluded", False) or agent.id in (
            "platform-manager",
            "platform-builder",
            "platform-engineer",
            "platform-manager-internal",
            "platform-builder-internal",
        ):
            raise CompanyError(403, "platform_worker", "Platform specialists cannot be Company task workers")
        if not principal.provider.check(
            AuthorizationContext(
                principal_id=principal.id,
                scopes=list(principal.scopes),
                claims=dict(principal.claims),
                resource_type="agents",
                resource_id=agent_id,
                action="run",
                admin_scope="agent_os:admin",
            )
        ):
            raise CompanyError(403, "worker_forbidden", "This worker is not authorized for the caller")
        return agent

    def _require_engineer(self, agent: Any) -> None:
        from agno.agents.claude import ClaudeAgent
        from agno.agents.codex import CodexAgent

        if (
            not isinstance(agent, (CodexAgent, ClaudeAgent))
            or getattr(agent, "sandbox", None) is None
            or isinstance(getattr(agent, "sandbox", None), str)
        ):
            raise CompanyError(409, "sandbox_required", "Repository work requires a sandboxed Product Engineer")
        try:
            from importlib import import_module

            import_module("agno.sandbox.repository")
        except ImportError as exc:
            raise CompanyError(
                409,
                "sandbox_upgrade_required",
                "Install sandbox repository workspace support before running repository work",
            ) from exc

    def _source(self, conn: Any, product: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, str]:
        from agno.os.company.repository import _resolve_commit

        previous = _row(
            conn,
            "SELECT payload FROM agno_company.task_runs WHERE task_id=:id AND NOT skipped ORDER BY created_at DESC LIMIT 1",
            id=task["id"],
        )
        source = previous["payload"].get("kwargs", {}).get("repository") if previous else None
        if source:
            if source["url"] != product["repository"]["url"]:
                raise CompanyError(409, "source_changed", "Create a new Task when changing repositories")
            return source
        return _resolve_commit(product["repository"], self.service._config.github_token)

    def _reserve(
        self, principal: Principal, task_id: str, version: int, key: str, message: str, trigger: str
    ) -> Dict[str, Any]:
        if not 1 <= len(key) <= 200:
            raise CompanyError(422, "invalid_request_id", "Idempotency key must be 1-200 characters")
        task_id = str(task_id)
        run_id = str(uuid5(NAMESPACE_URL, _json(["company", task_id, principal.id, key])))
        request_hash = hashlib.sha256(
            _json([version if trigger != "schedule" else None, message, trigger]).encode()
        ).hexdigest()
        service = self.service
        with service._transaction(principal) as conn:
            task, product = service._load(conn, principal, "task", task_id, lock=True)
            service._require(principal, product, "contributor", "write")
            existing = _row(conn, "SELECT * FROM agno_company.task_runs WHERE id=:id", id=run_id)
            if existing:
                self._agent(principal, existing["agent_id"])
                if existing["request_hash"] != request_hash:
                    raise CompanyError(409, "idempotency_mismatch", "Run key was used with different inputs")
                return existing
            if trigger == "ready" and (
                task["status"] != "ready"
                or not task["ready_principal"]
                or task["ready_principal"] != self._saved(principal)
                or task["ready_agent_id"] != (task["agent_id"] or product["agent_id"])
            ):
                raise CompanyError(
                    409, "ready_changed", "Return to Backlog and accept Ready again to authorize this worker"
                )
            if task["version"] != version:
                raise CompanyError(412, "version_conflict", "Reload the Task before running it")
            if task["state"] != "active" or product["state"] != "active":
                raise CompanyError(409, "archived_parent", "Restore the work before running it")
            project = None
            if task["project_id"]:
                project = _row(conn, "SELECT * FROM agno_company.projects WHERE id=:id", id=task["project_id"])
                if project is None or project["state"] != "active" or task["status"] not in ("ready", "in_progress"):
                    raise CompanyError(
                        409, "not_ready", "A Project Task must be Ready or awaiting another work attempt"
                    )
            if not task["instructions"]:
                raise CompanyError(409, "instructions_required", "Add instructions before running the Task")
            agent = self._agent(principal, task["agent_id"] or product["agent_id"])
            repository = None
            if product.get("repository") and getattr(agent, "sandbox", None) is not None:
                self._require_engineer(agent)
                if not project or not task.get("source") or not task["accepted_by"]:
                    raise CompanyError(
                        409,
                        "acceptance_required",
                        "Repository work requires a Project Task accepted as Ready by a human",
                    )
                repository = task["source"]
                if repository["url"] != product["repository"]["url"]:
                    raise CompanyError(409, "source_changed", "Accept this repository again before execution")
                busy = _query(
                    conn,
                    "SELECT 1 FROM agno_company.task_runs r JOIN agno_company.tasks t ON t.id=r.task_id WHERE t.product_id=:id AND NOT r.released AND r.payload->'kwargs' ? 'repository' LIMIT 1",
                    id=product["id"],
                ).scalar()
                if busy:
                    raise CompanyError(
                        409, "product_busy", "Another Product Engineer Task is running; this Task remains Ready"
                    )
            elif product.get("repository") and project:
                self._require_engineer(agent)
            active = _row(conn, "SELECT id FROM agno_company.task_runs WHERE task_id=:id AND NOT released", id=task_id)
            if active and trigger != "schedule":
                raise CompanyError(409, "run_active", "This Task already has an active run")
            previous = _row(
                conn,
                "SELECT * FROM agno_company.task_runs WHERE task_id=:id AND NOT skipped ORDER BY created_at DESC LIMIT 1",
                id=task_id,
            )
            session_id = (
                previous["session_id"]
                if project
                and previous
                and previous["agent_id"] == agent.id
                and previous["initiating_principal_id"] == principal.id
                else str(uuid4())
            )
            if repository and previous and previous["session_id"] != session_id:
                raise CompanyError(
                    409,
                    "engineer_changed",
                    "Continue with the original Product Engineer and user, or create a new Task",
                )
            prior_result = None
            if previous:
                prior_agent = next((a for a in self.os.agents or [] if a.id == previous["agent_id"]), None)
                if prior_agent:
                    prior = prior_agent.get_run_output(
                        run_id=str(previous["id"]),
                        session_id=previous["session_id"],
                        user_id=previous["initiating_principal_id"],
                    )
                    prior_result = str(getattr(prior, "content", "") or "")[:10000]
            prompt = {
                "previous_result": prior_result,
                "product": {"id": str(product["id"]), "name": product["name"], "instructions": product["instructions"]},
                "task": {"id": task_id, "title": task["title"], "instructions": task["instructions"]},
                "direction": message,
                "previous_run_id": str(previous["id"]) if previous else None,
            }
            if project:
                prompt["project"] = {
                    "id": str(project["id"]),
                    "title": project["title"],
                    "instructions": project["instructions"],
                }
            if not active and task["status"] == "ready":
                task = service._update(conn, "tasks", task_id, {"status": "in_progress", "automation_error": None})
            row = _row(
                conn,
                """INSERT INTO agno_company.task_runs
                (id,task_id,task_version,agent_id,initiating_principal_id,principal,payload,request_hash,session_id,trigger,released,skipped)
                VALUES (:id,:task,:version,:agent,:who,CAST(:principal AS jsonb),CAST(:payload AS jsonb),:hash,:session,:trigger,:skip,:skip) RETURNING *""",
                id=run_id,
                task=task_id,
                version=task["version"],
                agent=agent.id,
                who=principal.id,
                principal=_json(self._saved(principal)),
                payload=_json(
                    {
                        "input": _json(prompt),
                        "kwargs": {"repository": repository} if repository else {},
                        "scope": {"source": "registry"},
                    }
                ),
                hash=request_hash,
                session=session_id,
                trigger=trigger,
                skip=bool(active),
            )
            service._insert(
                conn,
                "activity",
                {
                    "id": str(uuid4()),
                    "product_id": product["id"],
                    "subject_type": "task",
                    "subject_id": task_id,
                    "actor_id": principal.agent_id or principal.id,
                    "initiating_principal_id": principal.id,
                    "operation": "task.run_skipped" if active else "task.run_requested",
                    "delta": {"run_id": run_id, "agent_id": agent.id},
                    "request_id": key,
                },
            )
            assert row is not None
            return row

    async def _enqueue(self, row: Dict[str, Any]) -> None:
        from agno.db.schemas.jobs import QueuedJob
        from agno.os.job_queue import aenqueue_ticket, aprepare_accepted_or_abort

        # A cancelled intent may have been saved after this caller reserved the run.
        row = await self._result_for_job({"id": str(row["id"])})
        if row["released"] or row["cancel_requested"]:
            return
        principal = self._principal(row["principal"])
        agent = await asyncio.to_thread(self._agent, principal, row["agent_id"])
        previous = await agent.aget_run_output(
            run_id=str(row["id"]), session_id=row["session_id"], user_id=principal.id
        )
        status = getattr(getattr(previous, "status", None), "value", None)
        if status in ("COMPLETED", "ERROR", "CANCELLED"):
            await asyncio.to_thread(
                self._settle, row, {"COMPLETED": "completed", "ERROR": "failed", "CANCELLED": "cancelled"}[status]
            )
            return
        job = QueuedJob(
            id=str(row["id"]),
            component_type="agent",
            component_id=row["agent_id"],
            session_id=row["session_id"],
            user_id=principal.id,
            payload=row["payload"],
            max_attempts=1,
            deployment_id=self.worker.config.deployment_id,
            idempotency_key="company:" + str(row["id"]),
        ).to_dict()
        result = await aenqueue_ticket(self.worker, job, agent)
        if result["reason"] == "queue_full":
            raise CompanyError(429, "queue_full", "Queue is full; retry with the same idempotency key")
        if result["reason"] == "duplicate":
            if not result.get("job") or result["job"]["id"] != job["id"]:
                raise CompanyError(409, "dispatch_conflict", "The original dispatch cannot be reconciled")
            return
        await aprepare_accepted_or_abort(
            self.worker, agent, "agent", job["id"], row["session_id"], principal.id, row["payload"]["input"]
        )

    async def arun_task(
        self,
        *,
        principal: Principal,
        task_id: str,
        version: int,
        idempotency_key: str,
        message: str = "",
        trigger: str = "manual",
    ) -> Dict[str, Any]:
        if self.worker is None:
            raise CompanyError(503, "queue_required", "Task execution requires a running durable AgentOS queue")
        await self.alist_runs(principal=principal, task_id=task_id)
        row = await asyncio.to_thread(self._reserve, principal, task_id, version, idempotency_key, message, trigger)
        await self._enqueue(row)
        return await self._result(row)

    def run_task(self, **kwargs: Any) -> Dict[str, Any]:
        return asyncio.run(self.arun_task(**kwargs))

    def _rows(self, principal: Principal, task_id: str) -> list:
        with self.service._transaction(principal, read=True) as conn:
            self.service._load(conn, principal, "task", task_id)
            return [
                dict(r)
                for r in _query(
                    conn,
                    "SELECT * FROM agno_company.task_runs WHERE task_id=:id ORDER BY created_at DESC LIMIT 100",
                    id=task_id,
                ).mappings()
            ]

    async def _result(self, row: Dict[str, Any]) -> Dict[str, Any]:
        job = await self.worker.store.get_job(str(row["id"])) if self.worker and not row["skipped"] else None
        status = "cancelled" if row["cancel_requested"] else ("unavailable" if row["released"] else "dispatch_pending")
        if job is not None:
            status = job["status"]
        if job is None and not row["skipped"]:
            agent = next((a for a in self.os.agents or [] if a.id == row["agent_id"]), None)
            if agent is not None:
                output = await agent.aget_run_output(
                    run_id=str(row["id"]), session_id=row["session_id"], user_id=row["initiating_principal_id"]
                )
                status = {
                    "COMPLETED": "completed",
                    "ERROR": "failed",
                    "CANCELLED": "cancelled",
                    "PAUSED": "paused",
                }.get(
                    getattr(getattr(output, "status", None), "value", ""),
                    status,
                )
        return {
            "id": str(row["id"]),
            "task_id": str(row["task_id"]),
            "task_version": row["task_version"],
            "agent_id": row["agent_id"],
            "initiating_principal_id": row["initiating_principal_id"],
            "session_id": row["session_id"],
            "run_id": str(row["id"]) if not row["skipped"] else None,
            "trigger": row["trigger"],
            "created_at": row["created_at"],
            "result_url": "/company/v1/tasks/" + str(row["task_id"]) + "/runs/" + str(row["id"]),
            "status": "skipped" if row["skipped"] else status,
            "source": row["payload"].get("kwargs", {}).get("repository"),
        }

    async def alist_runs(self, *, principal: Principal, task_id: str) -> Dict[str, Any]:
        rows = await asyncio.to_thread(self._rows, principal, task_id)
        results = []
        for row in rows:
            result = await self._result(row)
            if result["status"] in ("completed", "failed", "cancelled") and not row["released"]:
                await asyncio.to_thread(self._settle, row, result["status"])
            results.append(result)
        return {"data": results}

    def list_runs(self, **kwargs: Any) -> Dict[str, Any]:
        return asyncio.run(self.alist_runs(**kwargs))

    def _settle(self, row: Dict[str, Any], status: str) -> None:
        # Runtime completion is not human acceptance. Reconciliation still works after owner revocation.
        with self.service._engine.begin() as conn:
            _query(
                conn,
                "SELECT id FROM agno_company.products WHERE id=(SELECT product_id FROM agno_company.tasks WHERE id=:id) FOR UPDATE",
                id=row["task_id"],
            )
            task = _row(conn, "SELECT * FROM agno_company.tasks WHERE id=:id FOR UPDATE", id=row["task_id"])
            assert task is not None
            changed = _query(
                conn,
                "UPDATE agno_company.task_runs SET released=true,reconciled_at=now() WHERE id=:id AND NOT released RETURNING id",
                id=row["id"],
            ).scalar()
            if changed:
                if status == "completed" and task["status"] == "in_progress":
                    self.service._update(
                        conn,
                        "tasks",
                        str(task["id"]),
                        {
                            "status": "in_review",
                            "review_started_at": datetime.now(timezone.utc),
                            "review_pull_request": None,
                            "review_principal": None,
                        },
                    )
                self.service._insert(
                    conn,
                    "activity",
                    {
                        "id": str(uuid4()),
                        "product_id": task["product_id"],
                        "subject_type": "task",
                        "subject_id": task["id"],
                        "actor_id": "agent:" + row["agent_id"],
                        "initiating_principal_id": row["initiating_principal_id"],
                        "operation": "task.run_finished",
                        "delta": {"run_id": str(row["id"]), "status": status},
                        "request_id": str(row["id"]),
                    },
                )

    def _stamp_caller(self, job: Dict[str, Any]) -> Dict[str, Any]:
        context = current_company.get()
        payload = {k: v for k, v in (job.get("payload") or {}).items() if k != "company_caller"}
        if context is not None and context.service is self.service and job.get("user_id") == context.principal.id:
            payload["company_caller"] = {"principal": self._saved(context.principal), "product_id": context.product_id}
        return {**job, "payload": payload}

    def _claim_context(self, job: Dict[str, Any]) -> Optional[CompanyContext]:
        if not (job.get("idempotency_key") or "").startswith("company:"):
            caller = (job.get("payload") or {}).get("company_caller")
            if caller is None:
                return None
            principal = self._principal(caller["principal"])
            if principal.id != job.get("user_id"):
                raise CompanyError(403, "caller_mismatch", "The saved Company caller does not own this run")
            self.service._human(principal, principal.id)
            return CompanyContext(self.service, principal, caller.get("product_id"))
        with self.service._engine.connect() as conn:
            row = _row(conn, "SELECT * FROM agno_company.task_runs WHERE id=:id", id=job["id"])
        if row is None:
            return None
        if row["cancel_requested"]:
            raise CompanyError(409, "dispatch_cancelled", "Task execution was cancelled")
        principal = self._principal(row["principal"])
        with self.service._transaction(principal) as conn:
            task, product = self.service._load(conn, principal, "task", str(row["task_id"]))
            self.service._require(principal, product, "contributor", "write")
            self._agent(principal, row["agent_id"])
            if row["released"] or task["state"] != "active" or product["state"] != "active":
                raise CompanyError(403, "dispatch_revoked", "Task execution is no longer authorized")
            if (
                job["user_id"] != principal.id
                or job["component_id"] != row["agent_id"]
                or job["session_id"] != row["session_id"]
            ):
                raise CompanyError(403, "dispatch_mismatch", "Task execution does not match its saved authority")
            if row["payload"].get("kwargs", {}).get("repository"):
                self._require_engineer(self._agent(principal, row["agent_id"]))
                if (task["agent_id"] or product["agent_id"]) != row["agent_id"]:
                    raise CompanyError(403, "dispatch_revoked", "Product Engineer assignment changed")
                if job["payload"].get("kwargs") != row["payload"].get("kwargs"):
                    raise CompanyError(403, "dispatch_mismatch", "Repository source changed after acceptance")
            if task["project_id"]:
                parent = _row(conn, "SELECT state FROM agno_company.projects WHERE id=:id", id=task["project_id"])
                if parent is None or parent["state"] != "active":
                    raise CompanyError(403, "dispatch_revoked", "Project is archived")
        return CompanyContext(
            self.service,
            replace(principal, agent_id="agent:" + row["agent_id"], product_id=str(task["product_id"])),
            str(task["product_id"]),
        )

    async def _execute(self, worker: Any, job: Dict[str, Any], ownership: Any) -> None:
        try:
            context = await asyncio.to_thread(self._claim_context, job)
        except CompanyError as exc:
            cancelled = exc.code == "dispatch_cancelled"
            if await worker._persist_run_error(job, str(exc), status="cancelled" if cancelled else "error"):
                status = "cancelled" if cancelled else "failed"
                settled = await worker._asettle_ticket(job["id"], job["attempt"], status, str(exc))
                if settled and (job.get("idempotency_key") or "").startswith("company:"):
                    row = await self._result_for_job(job)
                    await asyncio.to_thread(self._settle, row, status)
            return
        token = current_company.set(context)
        try:
            await worker._execute_claimed_inner(job, ownership)
        finally:
            current_company.reset(token)
        if context is not None and (job.get("idempotency_key") or "").startswith("company:"):
            row = await self._result_for_job(job)
            result = await self._result(row)
            if result["status"] in ("completed", "failed", "cancelled"):
                await asyncio.to_thread(self._settle, row, result["status"])

    async def _result_for_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        def read() -> Dict[str, Any]:
            with self.service._engine.connect() as conn:
                row = _row(conn, "SELECT * FROM agno_company.task_runs WHERE id=:id", id=job["id"])
                assert row is not None
                return row

        return await asyncio.to_thread(read)

    def _load_run(self, principal: Principal, task_id: str, run_id: str, *, write: bool = False) -> Dict[str, Any]:
        with self.service._transaction(principal, read=not write) as conn:
            _, product = self.service._load(conn, principal, "task", task_id)
            if write:
                self.service._require(principal, product, "contributor", "write")
            row = _row(
                conn, "SELECT * FROM agno_company.task_runs WHERE task_id=:task AND id=:id", task=task_id, id=run_id
            )
            if row is None:
                raise CompanyError(404, "not_found", "Run not found for this Task")
            return row

    def _cancel_intent(self, principal: Principal, task_id: str, run_id: str) -> Dict[str, Any]:
        with self.service._transaction(principal) as conn:
            _, product = self.service._load(conn, principal, "task", task_id, lock=True)
            self.service._require(principal, product, "contributor", "write")
            row = _row(
                conn, "SELECT * FROM agno_company.task_runs WHERE id=:id AND task_id=:task", id=run_id, task=task_id
            )
            if row is None:
                raise CompanyError(404, "not_found", "Run not found for this Task")
            if not row["released"] and not row["cancel_requested"]:
                _query(conn, "UPDATE agno_company.task_runs SET cancel_requested=true WHERE id=:id", id=run_id)
                row["cancel_requested"] = True
                self.service._insert(
                    conn,
                    "activity",
                    {
                        "id": str(uuid4()),
                        "product_id": product["id"],
                        "subject_type": "task",
                        "subject_id": task_id,
                        "actor_id": principal.agent_id or principal.id,
                        "initiating_principal_id": principal.id,
                        "operation": "task.run_cancel_requested",
                        "delta": {"run_id": run_id},
                        "request_id": run_id,
                    },
                )
            return row

    async def acancel_task_run(self, *, principal: Principal, task_id: str, run_id: str) -> Dict[str, Any]:
        if self.worker is None:
            raise CompanyError(503, "queue_required", "Queue is unavailable")
        row = await asyncio.to_thread(self._cancel_intent, principal, task_id, run_id)
        await self.worker.acancel_queued(run_id)
        agent = next((a for a in self.os.agents or [] if a.id == row["agent_id"]), None)
        if agent is not None and row["cancel_requested"]:
            # Native cancellation interrupts an executing harness; queue cancellation only covers waiting tickets.
            await agent.acancel_run(run_id=run_id)
        result = await self._result(row)
        if result["status"] == "cancelled":
            await asyncio.to_thread(self._settle, row, "cancelled")
        return result

    def cancel_task_run(self, **kwargs: Any) -> Dict[str, Any]:
        return asyncio.run(self.acancel_task_run(**kwargs))

    def _schedule_manager(self) -> Any:
        from agno.scheduler import ScheduleManager

        if not self.os._scheduler_enabled or self.os.db is None or self.os.queue is None or not self.os.queue.durable:
            raise CompanyError(
                409, "scheduler_required", "Enable the AgentOS scheduler and durable queue with a runtime database"
            )
        return ScheduleManager(self.os.db)

    def _ensure_schedule(self, principal: Principal, task_id: str) -> Dict[str, Any]:
        task_id = str(task_id)
        manager = self._schedule_manager()
        try:
            with self.service._transaction(principal) as conn:
                task, product = self.service._load(conn, principal, "task", task_id, lock=True)
                self.service._require(principal, product, "owner", "manage")
                desired = task["schedule"]
                if not desired:
                    return task
                saved = task["schedule_principal"]
                endpoint = "/company/v1/tasks/" + task_id + "/runs"
                # Stable name and saved owner recover a lost create response without a second timer.
                schedule = manager.create(
                    name="company-task-" + task_id,
                    cron=desired["cron"],
                    timezone=desired["timezone"],
                    endpoint=endpoint,
                    user_id=saved["id"],
                    if_exists="skip",
                    max_retries=0,
                    provenance={"managed_by": "company", "target_type": "task", "target_id": task_id},
                )
                if task["schedule_id"] and task["schedule_id"] != schedule.id:
                    raise CompanyError(409, "schedule_conflict", "The recurring Task has a different schedule owner")
                from agno.scheduler.cron import compute_next_run

                changed = (
                    schedule.cron_expr != desired["cron"]
                    or schedule.timezone != desired["timezone"]
                    or schedule.enabled != desired["enabled"]
                )
                manager.update(
                    schedule.id,
                    cron_expr=desired["cron"],
                    timezone=desired["timezone"],
                    enabled=desired["enabled"],
                    endpoint=endpoint,
                    method="POST",
                    payload={},
                    max_retries=0,
                    next_run_at=compute_next_run(desired["cron"], desired["timezone"])
                    if changed
                    else schedule.next_run_at,
                )
                _query(
                    conn,
                    "UPDATE agno_company.tasks SET schedule_id=:schedule WHERE id=:id",
                    schedule=schedule.id,
                    id=task_id,
                )
                return {**task, "schedule_id": schedule.id}
        finally:
            manager.close()

    def set_schedule(self, *, principal: Principal, task_id: str, data: Any, **kwargs: Any) -> Dict[str, Any]:
        manager = self._schedule_manager()
        manager.close()
        self.service._mutate(
            principal=principal, kind="task", action="schedule", record_id=task_id, data=data, **kwargs
        )
        self._ensure_schedule(principal, task_id)
        return self.service.get_task(principal=principal, task_id=task_id)

    async def aset_schedule(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.set_schedule, **kwargs)

    async def _execute_schedule(self, schedule: Any) -> Dict[str, Any]:
        def read() -> Any:
            with self.service._engine.connect() as conn:
                return _row(
                    conn,
                    "SELECT * FROM agno_company.tasks WHERE id=:id AND schedule_id=:sid",
                    id=schedule.target_id,
                    sid=schedule.id,
                )

        task = await asyncio.to_thread(read)
        if not task or not task["schedule"] or not task["schedule"]["enabled"]:
            return {"status": "failed", "error": "Recurring Task is paused or missing"}
        saved = task["schedule_principal"]
        if (
            schedule.user_id != saved["id"]
            or schedule.endpoint != "/company/v1/tasks/" + str(task["id"]) + "/runs"
            or schedule.cron_expr != task["schedule"]["cron"]
            or schedule.timezone != task["schedule"]["timezone"]
        ):
            return {"status": "failed", "error": "Schedule no longer matches the Task's configured authority"}
        principal = self._principal(saved)
        try:
            # Use the due occurrence, never a fresh retry key. The poller advances from now after execution.
            key = "schedule:" + schedule.id + ":" + str(schedule.next_run_at)
            result = await self.arun_task(
                principal=principal,
                task_id=str(task["id"]),
                version=task["version"],
                idempotency_key=key,
                trigger="schedule",
            )
            deadline = time.monotonic() + (schedule.timeout_seconds or 3600)
            while result["status"] in ("dispatch_pending", "queued", "running"):
                if time.monotonic() >= deadline:
                    return {
                        "status": "failed",
                        "error": "Task run is still active at the schedule timeout",
                        "run_id": result["run_id"],
                        "session_id": result["session_id"],
                    }
                await asyncio.sleep(0.2)
                runs = await self.alist_runs(principal=principal, task_id=str(task["id"]))
                result = next(r for r in runs["data"] if r["id"] == result["id"])
            return {
                "status": "success" if result["status"] in ("completed", "skipped") else "failed",
                "status_code": 200,
                "run_id": result["run_id"],
                "session_id": result["session_id"],
                "output": {"task_status": result["status"]},
                "error": None if result["status"] in ("completed", "skipped") else "Task run did not complete",
            }
        except CompanyError as exc:
            return {"status": "failed", "status_code": exc.status, "error": str(exc)}

    async def _recover(self, *, schedules: bool = True) -> None:
        def read() -> Any:
            with self.service._engine.connect() as conn:
                from agno.os.company.migrations import VERSION

                if not _query(conn, "SELECT to_regclass('agno_company.task_runs')").scalar():
                    return [], []
                if _query(conn, "SELECT max(version) FROM agno_company.schema_version").scalar() != VERSION:
                    return [], []
                rows = [
                    dict(r)
                    for r in _query(
                        conn, "SELECT * FROM agno_company.task_runs WHERE NOT released ORDER BY created_at"
                    ).mappings()
                ]
                if not schedules:
                    return rows, []
                tasks = [
                    dict(r)
                    for r in _query(
                        conn, "SELECT id,schedule_principal FROM agno_company.tasks WHERE schedule IS NOT NULL"
                    ).mappings()
                ]
                return rows, tasks

        rows, tasks = await asyncio.to_thread(read)
        from agno.utils.log import log_warning

        for row in rows:
            try:
                await self._enqueue(row)
                result = await self._result(row)
                if result["status"] in ("completed", "failed", "cancelled"):
                    await asyncio.to_thread(self._settle, row, result["status"])
            except CompanyError as exc:
                log_warning(f"Company dispatch {row['id']} awaits operator action: {exc}")
        if self.os._scheduler_enabled:
            for task in tasks:
                try:
                    await asyncio.to_thread(
                        self._ensure_schedule, self._principal(task["schedule_principal"]), str(task["id"])
                    )
                except CompanyError as exc:
                    log_warning(f"Company schedule {task['id']} awaits operator action: {exc}")

    async def aget_task_result(self, *, principal: Principal, task_id: str, run_id: str) -> Dict[str, Any]:
        row = await asyncio.to_thread(self._load_run, principal, task_id, run_id)
        result = await self._result(row)
        agent = next((a for a in self.os.agents or [] if a.id == row["agent_id"]), None)
        output = None
        if agent is not None and not row["skipped"]:
            output = await agent.aget_run_output(
                run_id=str(row["id"]), session_id=row["session_id"], user_id=row["initiating_principal_id"]
            )
        result["content"] = getattr(output, "content", None)
        result["source"] = row["payload"].get("kwargs", {}).get("repository")
        return result

    def get_task_result(self, **kwargs: Any) -> Dict[str, Any]:
        return asyncio.run(self.aget_task_result(**kwargs))

    def _automation_tasks(self) -> list:
        from agno.os.company.migrations import VERSION

        with self.service._engine.connect() as conn:
            if not _query(conn, "SELECT to_regclass('agno_company.schema_version')").scalar():
                return []
            if _query(conn, "SELECT max(version) FROM agno_company.schema_version").scalar() != VERSION:
                return []
            return [
                dict(r)
                for r in _query(
                    conn,
                    """
                SELECT t.* FROM agno_company.tasks t
                JOIN agno_company.products p ON p.id=t.product_id
                JOIN agno_company.projects j ON j.id=t.project_id
                WHERE t.state='active' AND p.state='active' AND j.state='active' AND
                ((t.status='ready' AND t.ready_principal IS NOT NULL AND t.ready_agent_id IS NOT NULL)
                 OR (t.status='in_review' AND jsonb_typeof(t.review_pull_request)='object'))
                ORDER BY t.updated_at, t.id
            """,
                ).mappings()
            ]

    def _automation_error(self, task: Dict[str, Any], error: Optional[str]) -> None:
        # Diagnostics do not change the accepted Task version. A stale tick cannot overwrite a newer review.
        with self.service._engine.begin() as conn:
            _query(
                conn,
                "UPDATE agno_company.tasks SET automation_error=:error WHERE id=:id AND version=:version",
                id=task["id"],
                version=task["version"],
                error=error,
            )

    def _review_authority(self, conn: Any, task: Dict[str, Any], principal: Principal) -> Any:
        current, product = self.service._load(conn, principal, "task", str(task["id"]), lock=True)
        self.service._require(principal, product, "owner", "review")
        if (
            current["version"] != task["version"]
            or current["status"] != "in_review"
            or current["review_pull_request"] != task["review_pull_request"]
            or current["review_principal"] != task["review_principal"]
        ):
            raise CompanyError(412, "review_changed", "The Task review changed during verification")
        if "transition:done" not in self.service._actions(conn, principal, "task", current, product):
            raise CompanyError(409, "review_unavailable", "This Task is no longer available for review")
        return current, product

    def _check_review(self, task: Dict[str, Any]) -> Principal:
        principal = self._principal(task["review_principal"])
        with self.service._transaction(principal) as conn:
            self._review_authority(conn, task, principal)
        return principal

    def _accept_merge(self, task: Dict[str, Any], principal: Principal, proof: Dict[str, Any]) -> None:
        with self.service._transaction(principal) as conn:
            current, product = self._review_authority(conn, task, principal)
            changes = self.service._transition(
                conn,
                principal,
                "task",
                current,
                product,
                {
                    "to_status": "done",
                    "reason": "GitHub confirmed the reviewer-approved PR revision was merged",
                    "acceptance_check": "Verified merged revision and GitHub user account",
                    "evidence": []
                    if len(current["evidence"]) >= 20 or any(e["url"] == proof["url"] for e in current["evidence"])
                    else [{"type": "pull_request", "url": proof["url"], "label": "Verified merged pull request"}],
                },
            )
            self.service._update(conn, "tasks", str(task["id"]), changes)
            self.service._insert(
                conn,
                "activity",
                {
                    "id": str(uuid4()),
                    "product_id": product["id"],
                    "subject_type": "task",
                    "subject_id": task["id"],
                    "actor_id": "service:github",
                    "initiating_principal_id": principal.id,
                    "operation": "task.pull_request_merged",
                    "delta": {
                        "verification": proof,
                        "review_version": task["version"],
                        "before_status": "in_review",
                        "after_status": "done",
                    },
                    "request_id": "merge:" + str(task["id"]) + ":" + str(task["version"]),
                },
            )

    async def _tick(self) -> None:
        """Use the existing scheduler tick and queue; never create agents or a second timer."""
        if self.worker is None:
            return
        tasks = await asyncio.to_thread(self._automation_tasks)
        # Reconcile interrupted queue submissions and terminal results even without an HTTP reader.
        await self._recover(schedules=False)
        from agno.os.company.review import _verify_merge

        for task in sorted(tasks, key=lambda task: task["status"] != "ready"):
            try:
                if task["status"] == "ready":
                    await self.arun_task(
                        principal=self._principal(task["ready_principal"]),
                        task_id=str(task["id"]),
                        version=task["version"],
                        trigger="ready",
                        idempotency_key="ready:" + str(task["id"]) + ":" + task["accepted_at"].isoformat(),
                    )
                else:
                    principal = await asyncio.to_thread(self._check_review, task)
                    if not task["review_started_at"]:
                        raise CompanyError(
                            409, "review_required", "Request revision and start a new review before linking a PR"
                        )
                    proof = await _verify_merge(
                        task["review_pull_request"], task["review_started_at"], self.service._config.github_token
                    )
                    if proof is not None:
                        await asyncio.to_thread(self._accept_merge, task, principal, proof)
                await asyncio.to_thread(self._automation_error, task, None)
            except CompanyError as exc:
                await asyncio.to_thread(self._automation_error, task, str(exc))
