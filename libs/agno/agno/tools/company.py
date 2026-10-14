"""Product management tools using AgentOS's verified Company context."""

import asyncio
from dataclasses import replace
from typing import Any, Dict, Literal, Optional
from uuid import UUID, uuid4

from agno.os.company.context import current_company
from agno.os.company.policy import CompanyError
from agno.os.company.schemas import CommentCreate, ListQuery, ProjectCreate, ProjectSummary, TaskCreate, TaskPatch
from agno.run import RunContext
from agno.tools import Toolkit


class CompanyTools(Toolkit):
    """Manage Company work; human acceptance and platform management are deliberately absent.

    Construct once, then attach to an ordinary Agent. AgentOS supplies verified
    identity per execution, including when the OS Manager delegates to that Agent.
    Direct Python calls without a trusted execution context fail closed.
    """

    def __init__(self, **kwargs: Any):
        names = (
            "list_products",
            "list_work",
            "get_work",
            "create_project",
            "create_task",
            "update_task",
            "comment",
            "update_summary",
            "run_task",
            "group_task",
            "read_result",
        )
        super().__init__(
            name="company",
            tools=[getattr(self, name) for name in names],
            async_tools=[(getattr(self, "a" + name), name) for name in names],
            instructions="Read existing Company work before creating it. Keep task instructions and human acceptance intact. Refresh summaries only from current task versions. A successful run needs human review before Done.",
            **kwargs,
        )

    def _context(self, agent: Any, run_context: Optional[RunContext]) -> Any:
        context = current_company.get()
        if (
            context is None
            or run_context is None
            or run_context.user_id != context.principal.id
            or not getattr(agent, "id", None)
        ):
            raise CompanyError(403, "trusted_context_required", "Company tools require a verified AgentOS execution")
        return context.service, replace(context.principal, agent_id="agent:" + agent.id, product_id=context.product_id)

    def _mutation(self, principal: Any, key: str) -> Dict[str, Any]:
        return {"principal": principal, "idempotency_key": key, "request_id": str(uuid4())}

    def list_products(self, agent: Any, _agno_run_context: Optional[RunContext] = None) -> Dict[str, Any]:
        """List Products the initiating user can access."""
        service, principal = self._context(agent, _agno_run_context)
        return service.list_products(principal=principal)

    async def alist_products(self, agent: Any, _agno_run_context: Optional[RunContext] = None) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list_products, agent, _agno_run_context)

    def list_work(
        self,
        product_id: str,
        agent: Any,
        project_id: Optional[str] = None,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        """Read Projects and Tasks, including their versions, before creating or updating work."""
        service, principal = self._context(agent, _agno_run_context)
        query = ListQuery(product_id=UUID(product_id), project_id=UUID(project_id) if project_id else None)
        return {
            "projects": service.list_projects(principal=principal, query=ListQuery(product_id=UUID(product_id))),
            "tasks": service.list_tasks(principal=principal, query=query),
        }

    async def alist_work(
        self,
        product_id: str,
        agent: Any,
        project_id: Optional[str] = None,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list_work, product_id, agent, project_id, _agno_run_context)

    def get_work(
        self,
        kind: Literal["product", "project", "task"],
        record_id: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        """Read one Product, Project or Task using its immutable id."""
        service, principal = self._context(agent, _agno_run_context)
        return getattr(service, "get_" + kind)(principal=principal, **{kind + "_id": record_id})

    async def aget_work(
        self,
        kind: Literal["product", "project", "task"],
        record_id: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self.get_work, kind, record_id, agent, _agno_run_context)

    def create_project(
        self,
        product_id: str,
        title: str,
        instructions: str,
        request_key: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        """Create Project work after checking for an existing Project. Reuse request_key on retries."""
        service, principal = self._context(agent, _agno_run_context)
        return service.create_project(
            product_id=product_id,
            data=ProjectCreate(title=title, instructions=instructions),
            **self._mutation(principal, request_key),
        )

    async def acreate_project(
        self,
        product_id: str,
        title: str,
        instructions: str,
        request_key: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.create_project, product_id, title, instructions, request_key, agent, _agno_run_context
        )

    def create_task(
        self,
        product_id: str,
        title: str,
        instructions: str,
        request_key: str,
        agent: Any,
        project_id: Optional[str] = None,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        """Create a draft Task. Ownership is inherited; no authority or worker is chosen by the model."""
        service, principal = self._context(agent, _agno_run_context)
        return service.create_task(
            product_id=product_id,
            data=TaskCreate(
                title=title, instructions=instructions, project_id=UUID(project_id) if project_id else None
            ),
            **self._mutation(principal, request_key),
        )

    async def acreate_task(
        self,
        product_id: str,
        title: str,
        instructions: str,
        request_key: str,
        agent: Any,
        project_id: Optional[str] = None,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.create_task, product_id, title, instructions, request_key, agent, project_id, _agno_run_context
        )

    def update_task(
        self,
        task_id: str,
        version: int,
        instructions: str,
        request_key: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        """Update draft instructions using the version read from the Task."""
        service, principal = self._context(agent, _agno_run_context)
        return service.update_task(
            task_id=task_id,
            version=version,
            data=TaskPatch(instructions=instructions),
            **self._mutation(principal, request_key),
        )

    async def aupdate_task(
        self,
        task_id: str,
        version: int,
        instructions: str,
        request_key: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.update_task, task_id, version, instructions, request_key, agent, _agno_run_context
        )

    def comment(
        self, task_id: str, body: str, request_key: str, agent: Any, _agno_run_context: Optional[RunContext] = None
    ) -> Dict[str, Any]:
        """Attach findings or a result to a Task without changing accepted instructions."""
        service, principal = self._context(agent, _agno_run_context)
        return service.add_comment_task(
            task_id=task_id, data=CommentCreate(body=body), **self._mutation(principal, request_key)
        )

    async def acomment(
        self, task_id: str, body: str, request_key: str, agent: Any, _agno_run_context: Optional[RunContext] = None
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self.comment, task_id, body, request_key, agent, _agno_run_context)

    def update_summary(
        self,
        project_id: str,
        version: int,
        summary: str,
        source_versions: Dict[str, int],
        request_key: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        """Refresh a generated summary using every current unarchived Task id and version."""
        service, principal = self._context(agent, _agno_run_context)
        return service.update_project_summary(
            project_id=project_id,
            version=version,
            data=ProjectSummary(summary=summary, source_versions=source_versions),
            **self._mutation(principal, request_key),
        )

    async def aupdate_summary(
        self,
        project_id: str,
        version: int,
        summary: str,
        source_versions: Dict[str, int],
        request_key: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.update_summary, project_id, version, summary, source_versions, request_key, agent, _agno_run_context
        )

    def run_task(
        self, task_id: str, version: int, request_key: str, agent: Any, _agno_run_context: Optional[RunContext] = None
    ) -> Dict[str, Any]:
        """Run work using its human-configured worker. Project work must be Ready or awaiting an explicit retry or revision."""
        service, principal = self._context(agent, _agno_run_context)
        return service.run_task(
            task_id=task_id, version=version, idempotency_key=request_key, principal=principal, trigger="agent"
        )

    async def arun_task(
        self, task_id: str, version: int, request_key: str, agent: Any, _agno_run_context: Optional[RunContext] = None
    ) -> Dict[str, Any]:
        service, principal = self._context(agent, _agno_run_context)
        return await service.arun_task(
            task_id=task_id, version=version, idempotency_key=request_key, principal=principal, trigger="agent"
        )

    def group_task(
        self,
        task_id: str,
        version: int,
        project_id: Optional[str],
        request_key: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        """Group a draft Task into a Project, or detach it with null. Recurrence must be paused first."""
        service, principal = self._context(agent, _agno_run_context)
        return service.update_task(
            task_id=task_id,
            version=version,
            data=TaskPatch(project_id=UUID(project_id) if project_id else None),
            **self._mutation(principal, request_key),
        )

    async def agroup_task(
        self,
        task_id: str,
        version: int,
        project_id: Optional[str],
        request_key: str,
        agent: Any,
        _agno_run_context: Optional[RunContext] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.group_task, task_id, version, project_id, request_key, agent, _agno_run_context
        )

    def read_result(
        self, task_id: str, run_id: str, agent: Any, _agno_run_context: Optional[RunContext] = None
    ) -> Dict[str, Any]:
        """Read a Task's stored agent result without making another model call."""
        service, principal = self._context(agent, _agno_run_context)
        return service.get_task_result(task_id=task_id, run_id=run_id, principal=principal)

    async def aread_result(
        self, task_id: str, run_id: str, agent: Any, _agno_run_context: Optional[RunContext] = None
    ) -> Dict[str, Any]:
        service, principal = self._context(agent, _agno_run_context)
        return await service.aget_task_result(task_id=task_id, run_id=run_id, principal=principal)
