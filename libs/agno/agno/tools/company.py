"""Bounded Company tools for agents and direct MCP calls.

Identity is injected by the framework. No tool can accept or complete work,
reassign ownership, edit a Product brief, change Sources, or schedule work.
"""

import asyncio
import json
from dataclasses import asdict
from typing import Any, Optional

from agno.company.manager import AsyncCompanyManager, CompanyManager
from agno.company.playbook import _require_owner
from agno.db.base import AsyncBaseDb
from agno.run.authorization import current_authorization, requires_permission
from agno.tools import Toolkit


def _authority(run_context):
    return current_authorization() or getattr(run_context, "authorization", None)


def _identity(run_context):
    authority = _authority(run_context)
    return authority.context.principal_id if authority is not None else getattr(run_context, "user_id", None)


def _permission(resource, action, run_context):
    authority = _authority(run_context)
    if authority is not None:
        authority.require(resource, action)


async def _apermission(resource, action, run_context):
    authority = _authority(run_context)
    if authority is not None:
        await authority.arequire(resource, action)


def _page(result, limit, page):
    rows, total = result
    return json.dumps(
        {
            "data": rows,
            "meta": {"page": page, "limit": limit, "total_count": total, "total_pages": (total + limit - 1) // limit},
        },
        default=str,
    )


class CompanyTools(Toolkit):
    """Company-wide reads and proposal-only writes, following StudioTools injection.

    user_isolation is deployment configuration, never an argument offered to a
    model. Like HTTP, service accounts remain scoped even with isolation off.
    """

    def __init__(self, db: Any, *, user_isolation: bool = False, decision_tools: bool = True):
        self.db = db
        self.user_isolation = user_isolation
        names = [
            "list_company_products",
            "get_company_product",
            "list_company_projects",
            "list_company_tasks",
            "propose_company_project",
            "propose_company_task",
            "edit_company_project",
            "edit_company_task",
            "list_company_wiki",
            "read_company_wiki",
            "update_company_status",
        ]
        if decision_tools:
            names += ["log_company_decision", "search_company_decisions"]
        super().__init__(
            name="company",
            tools=[getattr(self, name) for name in names],
            async_tools=[(getattr(self, "a" + name), name) for name in names],
        )

    def _scoped_user(self, run_context):
        user = _identity(run_context)
        authority = _authority(run_context)
        if authority is not None:
            ctx = authority.context
            if (authority.service_account or authority.provider.enforces_token_scopes) and (
                (ctx.admin_scope or "agent_os:admin") in ctx.scopes
            ):
                return None
        if self.user_isolation or (isinstance(user, str) and user.startswith("sa:")):
            if not user:
                raise PermissionError("Caller identity is required under user isolation")
            return user
        return None

    def _sync(self):
        if isinstance(self.db, AsyncBaseDb):
            raise TypeError("Use async Company tools with an asynchronous database")
        return CompanyManager(self.db)

    def _async(self):
        if isinstance(self.db, AsyncBaseDb):
            return AsyncCompanyManager(self.db)
        return _AsyncSyncManager(CompanyManager(self.db))

    @requires_permission()
    def list_company_products(self, limit: int = 20, page: int = 1, _agno_run_context: Optional[Any] = None) -> str:
        """List every Product in the company."""
        _permission("products", "read", _agno_run_context)
        return _page(self._sync().list(limit=limit, page=page), limit, page)

    @requires_permission()
    def get_company_product(self, product_id: str, _agno_run_context: Optional[Any] = None) -> str:
        """Read a Product's purpose and current configuration."""
        _permission("products", "read", _agno_run_context)
        product = self._sync().get(product_id)
        if product is None:
            raise LookupError("Product not found")
        return json.dumps(product)

    @requires_permission()
    def list_company_projects(
        self, product_id: Optional[str] = None, limit: int = 20, page: int = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List proposed and active Projects across owners."""
        _permission("projects", "read", _agno_run_context)
        return _page(self._sync().list_projects(product_id=product_id, limit=limit, page=page), limit, page)

    @requires_permission()
    def list_company_tasks(
        self,
        product_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """List Tasks across owners, optionally filtered by status."""
        _permission("tasks", "read", _agno_run_context)
        return _page(self._sync().list_tasks(product_id=product_id, status=status, limit=limit, page=page), limit, page)

    @requires_permission()
    def propose_company_project(
        self, product_id: str, name: str, outcome: Optional[str] = None, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Propose a Project for human review; never activate or complete it."""
        _permission("projects", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        return json.dumps(
            self._sync().create_project(product_id, name, outcome=outcome, user_id=_identity(_agno_run_context))
        )

    @requires_permission()
    def propose_company_task(
        self,
        product_id: str,
        title: str,
        brief: Optional[str] = None,
        project_id: Optional[str] = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Create Backlog work for a human to accept and choose an executor."""
        _permission("tasks", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        return json.dumps(
            self._sync().create_task(
                product_id, title, brief=brief, project_id=project_id, user_id=_identity(_agno_run_context)
            )
        )

    @requires_permission()
    def edit_company_project(
        self, project_id: str, name: str, outcome: str, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Edit a proposed Project owned by the caller; accepted work stays frozen."""
        _permission("projects", "write", _agno_run_context)
        manager = self._sync()
        row = manager.get_project(project_id)
        if row is None:
            raise LookupError("Project not found")
        user = self._scoped_user(_agno_run_context)
        _require_owner(row, user)
        if row["status"] != "proposed":
            raise ValueError("Only proposed Projects may be edited by Company tools")
        return json.dumps(
            manager.update_project(project_id, user_id=user, expected_status="proposed", name=name, outcome=outcome)
        )

    @requires_permission()
    def edit_company_task(self, task_id: str, title: str, brief: str, _agno_run_context: Optional[Any] = None) -> str:
        """Edit the title and brief of owned Backlog work; never change lifecycle or ownership."""
        _permission("tasks", "write", _agno_run_context)
        manager = self._sync()
        row = manager.get_task(task_id)
        if row is None:
            raise LookupError("Task not found")
        user = self._scoped_user(_agno_run_context)
        _require_owner(row, user)
        return json.dumps(manager.update_task(task_id, user_id=user, title=title, brief=brief))

    @requires_permission()
    def list_company_wiki(
        self, product_id: Optional[str] = None, limit: int = 20, page: int = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List the Product playbook, or the company playbook when product_id is omitted."""
        _permission("wiki", "read", _agno_run_context)
        rows, total = self._sync().list_wiki(product_id, limit=limit, page=page)
        return _page(([asdict(row) for row in rows], total), limit, page)

    @requires_permission()
    def read_company_wiki(
        self, path: str, product_id: Optional[str] = None, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Read a playbook page and its version before planning or editing."""
        _permission("wiki", "read", _agno_run_context)
        return json.dumps(asdict(self._sync().read_wiki(product_id, path)))

    @requires_permission()
    def update_company_status(
        self, product_id: str, content: str, expected_version: int, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Update status.md after reading it; supply the version read to prevent lost edits."""
        _permission("wiki", "write", _agno_run_context)
        return json.dumps(
            asdict(
                self._sync().write_wiki(
                    product_id, "status.md", content, expected_version, user_id=self._scoped_user(_agno_run_context)
                )
            )
        )

    @requires_permission()
    def log_company_decision(
        self,
        decision: str,
        reasoning: Optional[str] = None,
        context: Optional[str] = None,
        outcome: Optional[str] = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Append a decision with reasoning, context and observed outcome to the learning log."""
        from agno.registry._reserved import PRODUCT_MANAGER_ID

        _permission("decisions", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        return json.dumps(
            asdict(
                self._sync().log_decision(
                    decision,
                    reasoning,
                    context,
                    outcome,
                    user_id=_identity(_agno_run_context),
                    session_id=getattr(_agno_run_context, "session_id", None),
                    agent_id=PRODUCT_MANAGER_ID,
                )
            )
        )

    @requires_permission()
    def search_company_decisions(
        self,
        query: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 20,
        page: int = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Search the company decision log by text, agent, session or age."""
        _permission("decisions", "read", _agno_run_context)
        rows, total = self._sync().list_decisions(query, agent_id, session_id, days, limit, page)
        return _page(([asdict(row) for row in rows], total), limit, page)

    @requires_permission()
    async def alist_company_products(
        self, limit: int = 20, page: int = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List every Product in the company."""
        await _apermission("products", "read", _agno_run_context)
        return _page(await self._async().list(limit=limit, page=page), limit, page)

    @requires_permission()
    async def aget_company_product(self, product_id: str, _agno_run_context: Optional[Any] = None) -> str:
        """Read a Product's purpose and current configuration."""
        await _apermission("products", "read", _agno_run_context)
        product = await self._async().get(product_id)
        if product is None:
            raise LookupError("Product not found")
        return json.dumps(product)

    @requires_permission()
    async def alist_company_projects(
        self, product_id: Optional[str] = None, limit: int = 20, page: int = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List proposed and active Projects across owners."""
        await _apermission("projects", "read", _agno_run_context)
        return _page(await self._async().list_projects(product_id=product_id, limit=limit, page=page), limit, page)

    @requires_permission()
    async def alist_company_tasks(
        self,
        product_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """List Tasks across owners, optionally filtered by status."""
        await _apermission("tasks", "read", _agno_run_context)
        return _page(
            await self._async().list_tasks(product_id=product_id, status=status, limit=limit, page=page), limit, page
        )

    @requires_permission()
    async def apropose_company_project(
        self, product_id: str, name: str, outcome: Optional[str] = None, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Propose a Project for human review; never activate or complete it."""
        await _apermission("projects", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        return json.dumps(
            await self._async().create_project(product_id, name, outcome=outcome, user_id=_identity(_agno_run_context))
        )

    @requires_permission()
    async def apropose_company_task(
        self,
        product_id: str,
        title: str,
        brief: Optional[str] = None,
        project_id: Optional[str] = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Create Backlog work for a human to accept and choose an executor."""
        await _apermission("tasks", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        return json.dumps(
            await self._async().create_task(
                product_id, title, brief=brief, project_id=project_id, user_id=_identity(_agno_run_context)
            )
        )

    @requires_permission()
    async def aedit_company_project(
        self, project_id: str, name: str, outcome: str, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Edit a proposed Project owned by the caller; accepted work stays frozen."""
        await _apermission("projects", "write", _agno_run_context)
        manager = self._async()
        row = await manager.get_project(project_id)
        if row is None:
            raise LookupError("Project not found")
        user = self._scoped_user(_agno_run_context)
        _require_owner(row, user)
        if row["status"] != "proposed":
            raise ValueError("Only proposed Projects may be edited by Company tools")
        return json.dumps(
            await manager.update_project(
                project_id, user_id=user, expected_status="proposed", name=name, outcome=outcome
            )
        )

    @requires_permission()
    async def aedit_company_task(
        self, task_id: str, title: str, brief: str, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Edit the title and brief of owned Backlog work; never change lifecycle or ownership."""
        await _apermission("tasks", "write", _agno_run_context)
        manager = self._async()
        row = await manager.get_task(task_id)
        if row is None:
            raise LookupError("Task not found")
        user = self._scoped_user(_agno_run_context)
        _require_owner(row, user)
        return json.dumps(await manager.update_task(task_id, user_id=user, title=title, brief=brief))

    @requires_permission()
    async def alist_company_wiki(
        self, product_id: Optional[str] = None, limit: int = 20, page: int = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List the Product playbook, or the company playbook when product_id is omitted."""
        await _apermission("wiki", "read", _agno_run_context)
        rows, total = await self._async().list_wiki(product_id, limit=limit, page=page)
        return _page(([asdict(row) for row in rows], total), limit, page)

    @requires_permission()
    async def aread_company_wiki(
        self, path: str, product_id: Optional[str] = None, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Read a playbook page and its version before planning or editing."""
        await _apermission("wiki", "read", _agno_run_context)
        return json.dumps(asdict(await self._async().read_wiki(product_id, path)))

    @requires_permission()
    async def aupdate_company_status(
        self, product_id: str, content: str, expected_version: int, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Update status.md after reading it; supply the version read to prevent lost edits."""
        await _apermission("wiki", "write", _agno_run_context)
        return json.dumps(
            asdict(
                await self._async().write_wiki(
                    product_id, "status.md", content, expected_version, user_id=self._scoped_user(_agno_run_context)
                )
            )
        )

    @requires_permission()
    async def alog_company_decision(
        self,
        decision: str,
        reasoning: Optional[str] = None,
        context: Optional[str] = None,
        outcome: Optional[str] = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Append a decision with reasoning, context and observed outcome to the learning log."""
        from agno.registry._reserved import PRODUCT_MANAGER_ID

        await _apermission("decisions", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        return json.dumps(
            asdict(
                await self._async().log_decision(
                    decision,
                    reasoning,
                    context,
                    outcome,
                    user_id=_identity(_agno_run_context),
                    session_id=getattr(_agno_run_context, "session_id", None),
                    agent_id=PRODUCT_MANAGER_ID,
                )
            )
        )

    @requires_permission()
    async def asearch_company_decisions(
        self,
        query: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 20,
        page: int = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Search the company decision log by text, agent, session or age."""
        await _apermission("decisions", "read", _agno_run_context)
        rows, total = await self._async().list_decisions(query, agent_id, session_id, days, limit, page)
        return _page(([asdict(row) for row in rows], total), limit, page)


class _AsyncSyncManager:
    """Offload the existing sync service for async tool execution."""

    def __init__(self, manager):
        self.manager = manager

    def __getattr__(self, name):
        async def call(*args, **kwargs):
            return await asyncio.to_thread(getattr(self.manager, name), *args, **kwargs)

        return call
