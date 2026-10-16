"""Bounded Company tools for agents and direct MCP calls.

Identity is injected by the framework. No tool can accept or complete work,
reassign ownership, edit a Product brief, change local Sources, or schedule work.
"""

import asyncio
import json
from dataclasses import asdict
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BeforeValidator

from agno.company.manager import AsyncCompanyManager, CompanyManager
from agno.company.playbook import _require_owner
from agno.db.base import AsyncBaseDb
from agno.run.authorization import current_authorization, requires_permission
from agno.tools import Toolkit


def _empty_to_none(value: Any) -> Any:
    """Treat a model's empty optional argument as omitted, preserving other values."""
    return None if value == "" else value


# Keep nullable schemas and normalize empty strings before Pydantic validation.
_OptionalString = Annotated[Optional[str], BeforeValidator(_empty_to_none)]
_OptionalInt = Annotated[Optional[int], BeforeValidator(_empty_to_none)]
_OptionalSourceConfig = Annotated[Optional[Dict[str, List[str]]], BeforeValidator(_empty_to_none)]


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


def _require_plain_proposal(run_context):
    from agno.company.routines import _RoutineAuthorization

    if isinstance(_authority(run_context), _RoutineAuthorization):
        raise PermissionError(
            "Routines must propose Tasks through intake_company_source with evidence and a dedupe key"
        )


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

    def __init__(
        self,
        db: Any,
        *,
        user_isolation: bool = False,
        decision_tools: bool = True,
        summary_tools: bool = True,
        refresh_tools: bool = True,
        agent_id: Optional[str] = None,
        interfaces: Any = None,
    ):
        self._interfaces_explicit = interfaces is not None
        self.interfaces = interfaces if interfaces is not None else []
        self._schedule_db = db
        self.db = db
        self.user_isolation = user_isolation
        # Supplied by the learning machine, never by the model or an MCP argument.
        self._agent_id = agent_id
        names = [
            "list_company_sources",
            "add_company_source",
            "read_company_source",
            "intake_company_source",
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
        if summary_tools:
            names += ["summarize_company_product"]
        if refresh_tools:
            names += ["refresh_company_product"]
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
        return CompanyManager(self.db, schedule_db=self._schedule_db)

    def _async(self):
        if isinstance(self.db, AsyncBaseDb):
            return AsyncCompanyManager(self.db, schedule_db=self._schedule_db)
        return _AsyncSyncManager(CompanyManager(self.db, schedule_db=self._schedule_db))

    @requires_permission()
    def list_company_products(
        self, limit: _OptionalInt = 20, page: _OptionalInt = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List every Product in the company.

        Args:
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
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
        self,
        product_id: _OptionalString = None,
        limit: _OptionalInt = 20,
        page: _OptionalInt = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """List proposed and active Projects across owners.

        Args:
            product_id: Product ID; null includes all Products.
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        product_id = _empty_to_none(product_id)
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        _permission("projects", "read", _agno_run_context)
        return _page(self._sync().list_projects(product_id=product_id, limit=limit, page=page), limit, page)

    @requires_permission()
    def list_company_tasks(
        self,
        product_id: _OptionalString = None,
        status: _OptionalString = None,
        limit: _OptionalInt = 20,
        page: _OptionalInt = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """List Tasks across owners, optionally filtered by status.

        Args:
            product_id: Product ID; null includes all Products.
            status: Task status to filter by; null includes all statuses.
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        product_id = _empty_to_none(product_id)
        status = _empty_to_none(status)
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        _permission("tasks", "read", _agno_run_context)
        return _page(self._sync().list_tasks(product_id=product_id, status=status, limit=limit, page=page), limit, page)

    @requires_permission()
    def propose_company_project(
        self, product_id: str, name: str, outcome: _OptionalString = None, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Propose a Project for human review; never activate or complete it.

        Args:
            outcome: Expected or observed outcome; null leaves it unspecified.
        """
        outcome = _empty_to_none(outcome)
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
        brief: _OptionalString = None,
        project_id: _OptionalString = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Create Backlog work for a human to accept and choose an executor.

        Args:
            brief: Task brief; null leaves it unspecified.
            project_id: Project ID within the Product; null proposes work without a Project.
        """
        brief = _empty_to_none(brief)
        project_id = _empty_to_none(project_id)
        _require_plain_proposal(_agno_run_context)
        _permission("tasks", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        return json.dumps(
            self._sync().create_task(
                product_id,
                title,
                brief=brief,
                project_id=project_id,
                user_id=_identity(_agno_run_context),
                origin="routine" if getattr(_authority(_agno_run_context), "routine_id", None) else "product_manager",
                routine_id=getattr(_authority(_agno_run_context), "routine_id", None),
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
        self,
        product_id: _OptionalString = None,
        limit: _OptionalInt = 20,
        page: _OptionalInt = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """List the Product playbook, or the company playbook when product_id is omitted.

        Args:
            product_id: Product ID; null selects the company playbook.
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        product_id = _empty_to_none(product_id)
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        _permission("wiki", "read", _agno_run_context)
        rows, total = self._sync().list_wiki(product_id, limit=limit, page=page)
        return _page(([asdict(row) for row in rows], total), limit, page)

    @requires_permission()
    def read_company_wiki(
        self, path: str, product_id: _OptionalString = None, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Read a playbook page and its version before planning or editing.

        Args:
            product_id: Product ID; null selects the company playbook.
        """
        product_id = _empty_to_none(product_id)
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
        reasoning: _OptionalString = None,
        context: _OptionalString = None,
        outcome: _OptionalString = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Append a decision with reasoning, context and observed outcome to the learning log.

        Args:
            reasoning: Reason for the decision; null leaves it unspecified.
            context: Decision context; null leaves it unspecified.
            outcome: Expected or observed outcome; null leaves it unspecified.
        """
        reasoning = _empty_to_none(reasoning)
        context = _empty_to_none(context)
        outcome = _empty_to_none(outcome)
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
                    agent_id=self._agent_id,
                )
            )
        )

    @requires_permission()
    def search_company_decisions(
        self,
        query: _OptionalString = None,
        agent_id: _OptionalString = None,
        session_id: _OptionalString = None,
        days: _OptionalInt = None,
        limit: _OptionalInt = 20,
        page: _OptionalInt = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Search the company decision log by text, agent, session or age.

        Args:
            query: Text to search for; null includes all decision text.
            agent_id: Agent ID to filter by; null includes all agents.
            session_id: Session ID to filter by; null includes all sessions.
            days: Maximum age in days; null applies no age filter.
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        query = _empty_to_none(query)
        agent_id = _empty_to_none(agent_id)
        session_id = _empty_to_none(session_id)
        days = _empty_to_none(days)
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        _permission("decisions", "read", _agno_run_context)
        rows, total = self._sync().list_decisions(query, agent_id, session_id, days, limit, page)
        return _page(([asdict(row) for row in rows], total), limit, page)

    @requires_permission()
    async def alist_company_products(
        self, limit: _OptionalInt = 20, page: _OptionalInt = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List every Product in the company.

        Args:
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
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
        self,
        product_id: _OptionalString = None,
        limit: _OptionalInt = 20,
        page: _OptionalInt = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """List proposed and active Projects across owners.

        Args:
            product_id: Product ID; null includes all Products.
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        product_id = _empty_to_none(product_id)
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        await _apermission("projects", "read", _agno_run_context)
        return _page(await self._async().list_projects(product_id=product_id, limit=limit, page=page), limit, page)

    @requires_permission()
    async def alist_company_tasks(
        self,
        product_id: _OptionalString = None,
        status: _OptionalString = None,
        limit: _OptionalInt = 20,
        page: _OptionalInt = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """List Tasks across owners, optionally filtered by status.

        Args:
            product_id: Product ID; null includes all Products.
            status: Task status to filter by; null includes all statuses.
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        product_id = _empty_to_none(product_id)
        status = _empty_to_none(status)
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        await _apermission("tasks", "read", _agno_run_context)
        return _page(
            await self._async().list_tasks(product_id=product_id, status=status, limit=limit, page=page), limit, page
        )

    @requires_permission()
    async def apropose_company_project(
        self, product_id: str, name: str, outcome: _OptionalString = None, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Propose a Project for human review; never activate or complete it.

        Args:
            outcome: Expected or observed outcome; null leaves it unspecified.
        """
        outcome = _empty_to_none(outcome)
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
        brief: _OptionalString = None,
        project_id: _OptionalString = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Create Backlog work for a human to accept and choose an executor.

        Args:
            brief: Task brief; null leaves it unspecified.
            project_id: Project ID within the Product; null proposes work without a Project.
        """
        brief = _empty_to_none(brief)
        project_id = _empty_to_none(project_id)
        _require_plain_proposal(_agno_run_context)
        await _apermission("tasks", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        return json.dumps(
            await self._async().create_task(
                product_id,
                title,
                brief=brief,
                project_id=project_id,
                user_id=_identity(_agno_run_context),
                origin="routine" if getattr(_authority(_agno_run_context), "routine_id", None) else "product_manager",
                routine_id=getattr(_authority(_agno_run_context), "routine_id", None),
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
        self,
        product_id: _OptionalString = None,
        limit: _OptionalInt = 20,
        page: _OptionalInt = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """List the Product playbook, or the company playbook when product_id is omitted.

        Args:
            product_id: Product ID; null selects the company playbook.
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        product_id = _empty_to_none(product_id)
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        await _apermission("wiki", "read", _agno_run_context)
        rows, total = await self._async().list_wiki(product_id, limit=limit, page=page)
        return _page(([asdict(row) for row in rows], total), limit, page)

    @requires_permission()
    async def aread_company_wiki(
        self, path: str, product_id: _OptionalString = None, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Read a playbook page and its version before planning or editing.

        Args:
            product_id: Product ID; null selects the company playbook.
        """
        product_id = _empty_to_none(product_id)
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
        reasoning: _OptionalString = None,
        context: _OptionalString = None,
        outcome: _OptionalString = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Append a decision with reasoning, context and observed outcome to the learning log.

        Args:
            reasoning: Reason for the decision; null leaves it unspecified.
            context: Decision context; null leaves it unspecified.
            outcome: Expected or observed outcome; null leaves it unspecified.
        """
        reasoning = _empty_to_none(reasoning)
        context = _empty_to_none(context)
        outcome = _empty_to_none(outcome)
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
                    agent_id=self._agent_id,
                )
            )
        )

    @requires_permission()
    async def asearch_company_decisions(
        self,
        query: _OptionalString = None,
        agent_id: _OptionalString = None,
        session_id: _OptionalString = None,
        days: _OptionalInt = None,
        limit: _OptionalInt = 20,
        page: _OptionalInt = 1,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Search the company decision log by text, agent, session or age.

        Args:
            query: Text to search for; null includes all decision text.
            agent_id: Agent ID to filter by; null includes all agents.
            session_id: Session ID to filter by; null includes all sessions.
            days: Maximum age in days; null applies no age filter.
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        query = _empty_to_none(query)
        agent_id = _empty_to_none(agent_id)
        session_id = _empty_to_none(session_id)
        days = _empty_to_none(days)
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        await _apermission("decisions", "read", _agno_run_context)
        rows, total = await self._async().list_decisions(query, agent_id, session_id, days, limit, page)
        return _page(([asdict(row) for row in rows], total), limit, page)

    def _source_context(self, source_id, run_context):
        if run_context is None or not getattr(run_context, "run_id", None):
            raise ValueError("Source tools require the injected run context")
        return run_context.run_id

    @requires_permission()
    def add_company_source(
        self,
        product_id: str,
        type: str,
        reference: str,
        config: _OptionalSourceConfig = None,
        _agno_agent: Optional[Any] = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Save a discovered website Source. Local Sources must be added by a human.

        Identical additions return the existing Source; conflicting settings are refused.

        Args:
            config: Optional reader settings; null uses the default configuration.
        """
        _permission("sources", "write", _agno_run_context)
        config = _empty_to_none(config)
        row = self._sync().add_source(
            product_id,
            type,
            reference,
            agent_id=getattr(_agno_agent, "id", None),
            run_id=getattr(_agno_run_context, "run_id", None),
            config=config,
            user_id=_identity(_agno_run_context),
            scoped_user_id=self._scoped_user(_agno_run_context),
        )
        return json.dumps({key: value for key, value in row.items() if key != "credential_ref"}, default=str)

    @requires_permission()
    def list_company_sources(
        self, product_id: str, limit: _OptionalInt = 20, page: _OptionalInt = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List the readers configured for a Product.

        Args:
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        _permission("sources", "read", _agno_run_context)
        rows, total = self._sync().list_sources(product_id=product_id, limit=limit, page=page)
        return _page(
            ([{key: value for key, value in row.items() if key != "credential_ref"} for row in rows], total),
            limit,
            page,
        )

    @requires_permission()
    def read_company_source(
        self,
        source_id: str,
        path: _OptionalString = None,
        pattern: _OptionalString = None,
        offset: _OptionalInt = 0,
        limit: _OptionalInt = 20,
        content_offset: _OptionalInt = 0,
        max_chars: _OptionalInt = 8000,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Discover Source files, then read selected content within a bounded response.

        Omit path for a content-free index; pattern filters filenames with a glob.
        Page with offset/limit (1..100) and next_offset. Pass a returned path to
        read one document: max_chars (1..16000) caps content, next_content_offset
        continues it. content_hash identifies the full reader document; compare
        hashes across fragments and reread if changed. Every response is at most
        64 KiB. Intake accepts only observed links and their full content hashes.

        Args:
            path: Selected document path; null returns the file index.
            pattern: Filename glob for discovery; null includes all configured files.
            offset: Zero-based index offset; null uses 0.
            limit: Index page size from 1 to 100; null uses 20.
            content_offset: Zero-based content character offset; null uses 0.
            max_chars: Content character cap from 1 to 16000; null uses 8000.
        """
        path = _empty_to_none(path)
        pattern = _empty_to_none(pattern)
        offset = _empty_to_none(offset)
        offset = 0 if offset is None else offset
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        content_offset = _empty_to_none(content_offset)
        content_offset = 0 if content_offset is None else content_offset
        max_chars = _empty_to_none(max_chars)
        max_chars = 8000 if max_chars is None else max_chars
        _permission("sources", "read", _agno_run_context)
        run_id = self._source_context(source_id, _agno_run_context)
        return json.dumps(
            self._sync().browse_source(source_id, run_id, path, pattern, offset, limit, content_offset, max_chars)
        )

    @requires_permission()
    def intake_company_source(
        self,
        source_id: str,
        title: str,
        brief: str,
        proposal_key: str,
        evidence_links: List[str],
        evidence_hashes: Dict[str, str],
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Propose actionable work backed by selected Source links.

        Read the Source first. Use a stable proposal_key for the same issue across
        scans and edits, and a concise outcome and brief, not copied file content.
        Pass evidence_hashes mapping each selected link to its observed content_hash.
        Changed evidence is rejected: read again and reconsider the proposal.
        """
        _permission("sources", "read", _agno_run_context)
        _permission("tasks", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        run_id = self._source_context(source_id, _agno_run_context)
        return json.dumps(
            self._sync().intake(
                source_id,
                run_id,
                {
                    "title": title,
                    "brief": brief,
                    "proposal_key": proposal_key,
                    "evidence_links": evidence_links,
                    "evidence_hashes": evidence_hashes,
                },
                user_id=_identity(_agno_run_context),
                routine_id=getattr(_authority(_agno_run_context), "routine_id", None),
            )
        )

    @requires_permission()
    def refresh_company_product(self, product_id: str, _agno_run_context: Optional[Any] = None) -> str:
        """Propose Project completion and archive old terminal work using the Product's window."""
        from agno.company.routines import _RoutineAuthorization

        if not isinstance(_authority(_agno_run_context), _RoutineAuthorization):
            raise PermissionError("Refresh maintenance requires Routine authority")
        for resource, action in (
            ("products", "read"),
            ("projects", "read"),
            ("projects", "delete"),
            ("tasks", "read"),
            ("tasks", "delete"),
            ("wiki", "read"),
            ("wiki", "write"),
        ):
            _permission(resource, action, _agno_run_context)
        return json.dumps(self._sync().refresh(product_id, user_id=self._scoped_user(_agno_run_context)))

    @requires_permission()
    def summarize_company_product(
        self, product_id: str, narrative: str, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Deliver current work and attention counts to the configured interface and Product wiki."""
        _permission("products", "read", _agno_run_context)
        _permission("tasks", "read", _agno_run_context)
        _permission("wiki", "write", _agno_run_context)
        run_id = self._source_context(product_id, _agno_run_context)
        return json.dumps(
            self._sync().summarize(
                product_id, run_id, self.interfaces, narrative=narrative, user_id=self._scoped_user(_agno_run_context)
            )
        )

    @requires_permission()
    async def aadd_company_source(
        self,
        product_id: str,
        type: str,
        reference: str,
        config: _OptionalSourceConfig = None,
        _agno_agent: Optional[Any] = None,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Save a discovered website Source. Local Sources must be added by a human.

        Identical additions return the existing Source; conflicting settings are refused.

        Args:
            config: Optional reader settings; null uses the default configuration.
        """
        await _apermission("sources", "write", _agno_run_context)
        config = _empty_to_none(config)
        row = await self._async().add_source(
            product_id,
            type,
            reference,
            agent_id=getattr(_agno_agent, "id", None),
            run_id=getattr(_agno_run_context, "run_id", None),
            config=config,
            user_id=_identity(_agno_run_context),
            scoped_user_id=self._scoped_user(_agno_run_context),
        )
        return json.dumps({key: value for key, value in row.items() if key != "credential_ref"}, default=str)

    @requires_permission()
    async def alist_company_sources(
        self, product_id: str, limit: _OptionalInt = 20, page: _OptionalInt = 1, _agno_run_context: Optional[Any] = None
    ) -> str:
        """List the readers configured for a Product.

        Args:
            limit: Maximum results per page; null uses 20.
            page: One-based page number; null uses 1.
        """
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        page = _empty_to_none(page)
        page = 1 if page is None else page
        await _apermission("sources", "read", _agno_run_context)
        rows, total = await self._async().list_sources(product_id=product_id, limit=limit, page=page)
        return _page(
            ([{key: value for key, value in row.items() if key != "credential_ref"} for row in rows], total),
            limit,
            page,
        )

    @requires_permission()
    async def aread_company_source(
        self,
        source_id: str,
        path: _OptionalString = None,
        pattern: _OptionalString = None,
        offset: _OptionalInt = 0,
        limit: _OptionalInt = 20,
        content_offset: _OptionalInt = 0,
        max_chars: _OptionalInt = 8000,
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Discover Source files, then read selected content within a bounded response.

        Omit path for a content-free index; pattern filters filenames with a glob.
        Page with offset/limit (1..100) and next_offset. Pass a returned path to
        read one document: max_chars (1..16000) caps content, next_content_offset
        continues it. content_hash identifies the full reader document; compare
        hashes across fragments and reread if changed. Every response is at most
        64 KiB. Intake accepts only observed links and their full content hashes.

        Args:
            path: Selected document path; null returns the file index.
            pattern: Filename glob for discovery; null includes all configured files.
            offset: Zero-based index offset; null uses 0.
            limit: Index page size from 1 to 100; null uses 20.
            content_offset: Zero-based content character offset; null uses 0.
            max_chars: Content character cap from 1 to 16000; null uses 8000.
        """
        path = _empty_to_none(path)
        pattern = _empty_to_none(pattern)
        offset = _empty_to_none(offset)
        offset = 0 if offset is None else offset
        limit = _empty_to_none(limit)
        limit = 20 if limit is None else limit
        content_offset = _empty_to_none(content_offset)
        content_offset = 0 if content_offset is None else content_offset
        max_chars = _empty_to_none(max_chars)
        max_chars = 8000 if max_chars is None else max_chars
        await _apermission("sources", "read", _agno_run_context)
        run_id = self._source_context(source_id, _agno_run_context)
        return json.dumps(
            await self._async().browse_source(
                source_id, run_id, path, pattern, offset, limit, content_offset, max_chars
            )
        )

    @requires_permission()
    async def aintake_company_source(
        self,
        source_id: str,
        title: str,
        brief: str,
        proposal_key: str,
        evidence_links: List[str],
        evidence_hashes: Dict[str, str],
        _agno_run_context: Optional[Any] = None,
    ) -> str:
        """Propose actionable work backed by selected Source links.

        Read the Source first. Use a stable proposal_key for the same issue across
        scans and edits, and a concise outcome and brief, not copied file content.
        Pass evidence_hashes mapping each selected link to its observed content_hash.
        Changed evidence is rejected: read again and reconsider the proposal.
        """
        await _apermission("sources", "read", _agno_run_context)
        await _apermission("tasks", "write", _agno_run_context)
        self._scoped_user(_agno_run_context)
        run_id = self._source_context(source_id, _agno_run_context)
        return json.dumps(
            await self._async().intake(
                source_id,
                run_id,
                {
                    "title": title,
                    "brief": brief,
                    "proposal_key": proposal_key,
                    "evidence_links": evidence_links,
                    "evidence_hashes": evidence_hashes,
                },
                user_id=_identity(_agno_run_context),
                routine_id=getattr(_authority(_agno_run_context), "routine_id", None),
            )
        )

    @requires_permission()
    async def arefresh_company_product(self, product_id: str, _agno_run_context: Optional[Any] = None) -> str:
        """Propose Project completion and archive old terminal work using the Product's window."""
        from agno.company.routines import _RoutineAuthorization

        if not isinstance(_authority(_agno_run_context), _RoutineAuthorization):
            raise PermissionError("Refresh maintenance requires Routine authority")
        for resource, action in (
            ("products", "read"),
            ("projects", "read"),
            ("projects", "delete"),
            ("tasks", "read"),
            ("tasks", "delete"),
            ("wiki", "read"),
            ("wiki", "write"),
        ):
            await _apermission(resource, action, _agno_run_context)
        return json.dumps(await self._async().refresh(product_id, user_id=self._scoped_user(_agno_run_context)))

    @requires_permission()
    async def asummarize_company_product(
        self, product_id: str, narrative: str, _agno_run_context: Optional[Any] = None
    ) -> str:
        """Deliver current work and attention counts to the configured interface and Product wiki."""
        await _apermission("products", "read", _agno_run_context)
        await _apermission("tasks", "read", _agno_run_context)
        await _apermission("wiki", "write", _agno_run_context)
        run_id = self._source_context(product_id, _agno_run_context)
        return json.dumps(
            await self._async().summarize(
                product_id, run_id, self.interfaces, narrative=narrative, user_id=self._scoped_user(_agno_run_context)
            )
        )


class _AsyncSyncManager:
    """Offload the existing sync service for async tool execution."""

    def __init__(self, manager):
        self.manager = manager

    def __getattr__(self, name):
        async def call(*args, **kwargs):
            return await asyncio.to_thread(getattr(self.manager, name), *args, **kwargs)

        return call
