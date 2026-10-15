"""Synchronous and asynchronous management of Company Products."""

import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from agno.db.base import AsyncBaseDb, BaseDb
from agno.db.schemas.products import validate_product_fields


class CompanyManager:
    """Manage Products through a synchronous database.

    user_id=None leaves reads and writes unscoped; a string restricts them to
    that owner. On create it records the accountable owner.
    """

    def __init__(self, db: BaseDb, registry: Any = None):
        self.db = db
        self.registry = registry

    def create(
        self,
        name: str,
        purpose: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Product."""
        fields = {"name": name, "purpose": purpose, "metadata": metadata}
        validate_product_fields(fields)
        return self.db.create_product(
            {
                **fields,
                "id": str(uuid4()),
                "user_id": user_id,
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    def get(
        self, product_id: str, user_id: Optional[str] = None, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a visible Product, optionally including deleted records."""
        return self.db.get_product(product_id, user_id=user_id, include_deleted=include_deleted)

    def list(
        self, user_id: Optional[str] = None, limit: int = 20, page: int = 1, include_deleted: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Return a page of visible Products and the total before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        return self.db.get_products(user_id=user_id, limit=limit, page=page, include_deleted=include_deleted)

    def update(self, product_id: str, user_id: Optional[str] = None, **fields: Any) -> Optional[Dict[str, Any]]:
        """Update name, purpose or metadata on an active Product."""
        validate_product_fields(fields)
        return self.db.update_product(product_id, user_id=user_id, **fields)

    def delete(self, product_id: str, user_id: Optional[str] = None) -> bool:
        """Soft-delete a visible Product."""
        return self.db.delete_product(product_id, user_id=user_id)

    def restore(self, product_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a visible deleted Product; return None if it is already active."""
        return self.db.restore_product(product_id, user_id=user_id)

    def create_project(
        self,
        product_id: str,
        name: str,
        outcome: Optional[str] = None,
        target_date: Optional[int] = None,
        user_id: Optional[str] = None,
        scoped_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create project work; scoped_user_id filters parents while user_id records the creator."""
        from agno.db.schemas.projects import validate_project_fields

        fields = {"name": name, "outcome": outcome, "target_date": target_date}
        validate_project_fields(fields)
        if self.db.get_product(product_id, user_id=scoped_user_id) is None:
            raise LookupError("Product not found")
        return self.db.create_project(
            {
                **fields,
                "product_id": product_id,
                "id": str(uuid4()),
                "status": "proposed",
                "user_id": user_id,
                "transitions": [],
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    def get_project(
        self, project_id: str, user_id: Optional[str] = None, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a visible project, optionally including deleted records."""
        return self.db.get_project(project_id, user_id=user_id, include_deleted=include_deleted)

    def list_projects(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
        product_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List across Products, filtering status and owner before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        return self.db.get_projects(
            user_id=user_id,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            product_id=product_id,
            status=status,
        )

    def update_project(
        self, project_id: str, user_id: Optional[str] = None, expected_status: Optional[str] = None, **fields: Any
    ) -> Optional[Dict[str, Any]]:
        """Update the name, outcome or target date of a visible Project."""
        from agno.db.schemas.projects import validate_project_fields

        validate_project_fields(fields)
        if expected_status is not None:
            fields["expected_status"] = expected_status
        return self.db.update_project(project_id, user_id=user_id, **fields)

    def delete_project(self, project_id: str, user_id: Optional[str] = None) -> bool:
        """Soft-delete a visible project."""
        return self.db.delete_project(project_id, user_id=user_id)

    def restore_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a deleted project."""
        return self.db.restore_project(project_id, user_id=user_id)

    def transition_project(
        self,
        project_id: str,
        target: str,
        reason: str,
        user_id: Optional[str] = None,
        accepted_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Apply an explicit transition; the caller enforces platform authorization."""
        return self.db.transition_project(
            project_id,
            target,
            reason,
            user_id=user_id,
            accepted_by=accepted_by,
        )

    def create_task(
        self,
        product_id: str,
        title: str,
        brief: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        scoped_user_id: Optional[str] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create task work; scoped_user_id filters parents while user_id records the creator."""
        from agno.db.schemas.tasks import validate_task_fields

        fields = {"title": title, "brief": brief, "project_id": project_id, "evidence": evidence}
        validate_task_fields(fields)
        if self.db.get_product(product_id, user_id=scoped_user_id) is None:
            raise LookupError("Product not found")
        if project_id is not None:
            project = self.db.get_project(project_id, user_id=scoped_user_id)
            if project is None:
                raise LookupError("Project not found")
            if project["product_id"] != product_id:
                raise ValueError("Task and Project must belong to the same Product")
        return self.db.create_task(
            {
                **fields,
                "product_id": product_id,
                "id": str(uuid4()),
                "status": "backlog",
                "session_id": str(uuid4()),
                "user_id": user_id,
                "transitions": [],
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    def get_task(
        self, task_id: str, user_id: Optional[str] = None, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a visible task, optionally including deleted records."""
        return self.db.get_task(task_id, user_id=user_id, include_deleted=include_deleted)

    def list_tasks(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
        product_id: Optional[str] = None,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
        failed: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List across Products, filtering status and owner before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        return self.db.get_tasks(
            user_id=user_id,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            product_id=product_id,
            status=status,
            project_id=project_id,
            failed=failed,
        )

    def update_task(self, task_id: str, user_id: Optional[str] = None, **fields: Any) -> Optional[Dict[str, Any]]:
        """Update descriptive fields; accepted Task scope requires a return to Backlog."""
        from agno.db.schemas.tasks import validate_task_fields

        validate_task_fields(fields)
        existing = self.db.get_task(task_id, user_id=user_id)
        if existing is None:
            return None
        if existing["status"] != "backlog":
            raise ValueError("Accepted task scope requires a return to Backlog")
        if fields.get("project_id") is not None:
            project = self.db.get_project(fields["project_id"], user_id=None)
            if project is None:
                raise LookupError("Project not found")
            if project["product_id"] != existing["product_id"]:
                raise ValueError("Task and Project must belong to the same Product")
        return self.db.update_task(task_id, user_id=user_id, **fields)

    def delete_task(self, task_id: str, user_id: Optional[str] = None) -> bool:
        """Soft-delete a visible task."""
        return self.db.delete_task(task_id, user_id=user_id)

    def restore_task(self, task_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a deleted task."""
        return self.db.restore_task(task_id, user_id=user_id)

    def transition_task(
        self,
        task_id: str,
        target: str,
        reason: str,
        user_id: Optional[str] = None,
        accepted_by: Optional[str] = None,
        executor_type: Optional[str] = None,
        executor_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Apply an explicit transition; the caller enforces platform authorization."""
        if target == "ready" and self.registry is not None:
            from agno.company.execution import _executor

            _executor(self.registry, executor_type, executor_id, accepting=True)
        return self.db.transition_task(
            task_id,
            target,
            reason,
            user_id=user_id,
            accepted_by=accepted_by,
            executor_type=executor_type,
            executor_id=executor_id,
        )

    def start_task_run(
        self,
        task_id: str,
        attempt: int,
        expected_transitions: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        run_db_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Reserve accepted work; HTTP validates run authority before calling this method."""
        return self.db.start_task_run(task_id, attempt, expected_transitions, user_id=user_id, run_db_id=run_db_id)

    def complete_task_run(
        self,
        task_id: str,
        job_id: str,
        result: Dict[str, Any],
        expected_transitions: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Project the ordinary run result onto the current Task attempt."""
        return self.db.complete_task_run(task_id, job_id, result, expected_transitions=expected_transitions)

    def attention(self, product_id: Optional[str] = None) -> Dict[str, int]:
        """Company-wide counts over the same filters used by the Task list."""
        counts = {}
        for name, filters in (
            ("proposals", {"status": "backlog"}),
            ("in_review", {"status": "in_review"}),
            ("failed", {"failed": True}),
        ):
            _, counts[name] = self.list_tasks(product_id=product_id, limit=1, **filters)
        return counts

    def get_wiki(self, product_id: Optional[str] = None):
        """Return a Product or company wiki; reads are company-wide.

        Default pages are created atomically on first access and never reset.
        """
        from agno.company.playbook import _seed, _wiki

        product = self.get(product_id) if product_id is not None else None
        if product_id is not None and product is None:
            raise LookupError("Product not found")
        provider = _wiki(self.db, product)
        _seed(provider, product)
        return provider

    def list_wiki(self, product_id: Optional[str] = None, limit: int = 20, page: int = 1):
        """List wiki pages with the standard Company pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        provider = self.get_wiki(product_id)
        pages = provider.backend.filesystem.list()
        return pages[(page - 1) * limit : page * limit], len(pages)

    def read_wiki(self, product_id: Optional[str], path: str):
        """Read a Markdown page and its filesystem version."""
        from agno.company.playbook import _page_path

        provider = self.get_wiki(product_id)
        result = provider.backend.filesystem.read_with_meta(_page_path(path))
        if result is None:
            raise LookupError("Wiki page not found")
        return result

    def write_wiki(
        self, product_id: Optional[str], path: str, content: str, expected_version: int, user_id: Optional[str] = None
    ):
        """Write with a filesystem version check; a scoped caller must own the Product.

        Company-wide pages are unowned, like shared components, and therefore
        editable only by unscoped callers. Version zero means create only.
        """
        from agno.company.playbook import _page_path, _require_owner

        if expected_version < 0:
            raise ValueError("expected_version must be nonnegative")
        product = self.get(product_id) if product_id is not None else {}
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, user_id)
        provider = self.get_wiki(product_id)
        return provider.backend.filesystem.write(_page_path(path), content, expected_version=expected_version)

    def log_decision(
        self,
        decision: str,
        reasoning: Optional[str] = None,
        context: Optional[str] = None,
        outcome: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ):
        """Append an owned entry to the learning decision log, never a wiki page."""
        from agno.company.decisions import CompanyDecisionLogStore, _new_decision

        entry = _new_decision(decision, reasoning, context, outcome, user_id, session_id, agent_id)
        CompanyDecisionLogStore(self.db).save(entry)
        return entry

    def list_decisions(
        self,
        query: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 20,
        page: int = 1,
    ):
        """Search Company decisions across owners using the learning store's filters."""
        from agno.company.decisions import CompanyDecisionLogStore

        if limit < 1 or page < 1 or (days is not None and days < 1):
            raise ValueError("limit, page and days must be positive")
        entries = CompanyDecisionLogStore(self.db).search(
            query=query, agent_id=agent_id, session_id=session_id, days=days, limit=None
        )
        return entries[(page - 1) * limit : page * limit], len(entries)


class AsyncCompanyManager:
    """Manage Products through an asynchronous database.

    user_id=None leaves reads and writes unscoped; a string restricts them to
    that owner. On create it records the accountable owner.
    """

    def __init__(self, db: AsyncBaseDb, registry: Any = None):
        self.db = db
        self.registry = registry

    async def create(
        self,
        name: str,
        purpose: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Product."""
        fields = {"name": name, "purpose": purpose, "metadata": metadata}
        validate_product_fields(fields)
        return await self.db.create_product(
            {
                **fields,
                "id": str(uuid4()),
                "user_id": user_id,
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    async def get(
        self, product_id: str, user_id: Optional[str] = None, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a visible Product, optionally including deleted records."""
        return await self.db.get_product(product_id, user_id=user_id, include_deleted=include_deleted)

    async def list(
        self, user_id: Optional[str] = None, limit: int = 20, page: int = 1, include_deleted: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Return a page of visible Products and the total before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        return await self.db.get_products(user_id=user_id, limit=limit, page=page, include_deleted=include_deleted)

    async def update(self, product_id: str, user_id: Optional[str] = None, **fields: Any) -> Optional[Dict[str, Any]]:
        """Update name, purpose or metadata on an active Product."""
        validate_product_fields(fields)
        return await self.db.update_product(product_id, user_id=user_id, **fields)

    async def delete(self, product_id: str, user_id: Optional[str] = None) -> bool:
        """Soft-delete a visible Product."""
        return await self.db.delete_product(product_id, user_id=user_id)

    async def restore(self, product_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a visible deleted Product; return None if it is already active."""
        return await self.db.restore_product(product_id, user_id=user_id)

    async def create_project(
        self,
        product_id: str,
        name: str,
        outcome: Optional[str] = None,
        target_date: Optional[int] = None,
        user_id: Optional[str] = None,
        scoped_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create project work; scoped_user_id filters parents while user_id records the creator."""
        from agno.db.schemas.projects import validate_project_fields

        fields = {"name": name, "outcome": outcome, "target_date": target_date}
        validate_project_fields(fields)
        if await self.db.get_product(product_id, user_id=scoped_user_id) is None:
            raise LookupError("Product not found")
        return await self.db.create_project(
            {
                **fields,
                "product_id": product_id,
                "id": str(uuid4()),
                "status": "proposed",
                "user_id": user_id,
                "transitions": [],
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    async def get_project(
        self, project_id: str, user_id: Optional[str] = None, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a visible project, optionally including deleted records."""
        return await self.db.get_project(project_id, user_id=user_id, include_deleted=include_deleted)

    async def list_projects(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
        product_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List across Products, filtering status and owner before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        return await self.db.get_projects(
            user_id=user_id,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            product_id=product_id,
            status=status,
        )

    async def update_project(
        self, project_id: str, user_id: Optional[str] = None, expected_status: Optional[str] = None, **fields: Any
    ) -> Optional[Dict[str, Any]]:
        """Update the name, outcome or target date of a visible Project."""
        from agno.db.schemas.projects import validate_project_fields

        validate_project_fields(fields)
        if expected_status is not None:
            fields["expected_status"] = expected_status
        return await self.db.update_project(project_id, user_id=user_id, **fields)

    async def delete_project(self, project_id: str, user_id: Optional[str] = None) -> bool:
        """Soft-delete a visible project."""
        return await self.db.delete_project(project_id, user_id=user_id)

    async def restore_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a deleted project."""
        return await self.db.restore_project(project_id, user_id=user_id)

    async def transition_project(
        self,
        project_id: str,
        target: str,
        reason: str,
        user_id: Optional[str] = None,
        accepted_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Apply an explicit transition; the caller enforces platform authorization."""
        return await self.db.transition_project(
            project_id,
            target,
            reason,
            user_id=user_id,
            accepted_by=accepted_by,
        )

    async def create_task(
        self,
        product_id: str,
        title: str,
        brief: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        scoped_user_id: Optional[str] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create task work; scoped_user_id filters parents while user_id records the creator."""
        from agno.db.schemas.tasks import validate_task_fields

        fields = {"title": title, "brief": brief, "project_id": project_id, "evidence": evidence}
        validate_task_fields(fields)
        if await self.db.get_product(product_id, user_id=scoped_user_id) is None:
            raise LookupError("Product not found")
        if project_id is not None:
            project = await self.db.get_project(project_id, user_id=scoped_user_id)
            if project is None:
                raise LookupError("Project not found")
            if project["product_id"] != product_id:
                raise ValueError("Task and Project must belong to the same Product")
        return await self.db.create_task(
            {
                **fields,
                "product_id": product_id,
                "id": str(uuid4()),
                "status": "backlog",
                "session_id": str(uuid4()),
                "user_id": user_id,
                "transitions": [],
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    async def get_task(
        self, task_id: str, user_id: Optional[str] = None, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a visible task, optionally including deleted records."""
        return await self.db.get_task(task_id, user_id=user_id, include_deleted=include_deleted)

    async def list_tasks(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
        product_id: Optional[str] = None,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
        failed: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List across Products, filtering status and owner before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        return await self.db.get_tasks(
            user_id=user_id,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            product_id=product_id,
            status=status,
            project_id=project_id,
            failed=failed,
        )

    async def update_task(self, task_id: str, user_id: Optional[str] = None, **fields: Any) -> Optional[Dict[str, Any]]:
        """Update descriptive fields; accepted Task scope requires a return to Backlog."""
        from agno.db.schemas.tasks import validate_task_fields

        validate_task_fields(fields)
        existing = await self.db.get_task(task_id, user_id=user_id)
        if existing is None:
            return None
        if existing["status"] != "backlog":
            raise ValueError("Accepted task scope requires a return to Backlog")
        if fields.get("project_id") is not None:
            project = await self.db.get_project(fields["project_id"], user_id=None)
            if project is None:
                raise LookupError("Project not found")
            if project["product_id"] != existing["product_id"]:
                raise ValueError("Task and Project must belong to the same Product")
        return await self.db.update_task(task_id, user_id=user_id, **fields)

    async def delete_task(self, task_id: str, user_id: Optional[str] = None) -> bool:
        """Soft-delete a visible task."""
        return await self.db.delete_task(task_id, user_id=user_id)

    async def restore_task(self, task_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a deleted task."""
        return await self.db.restore_task(task_id, user_id=user_id)

    async def transition_task(
        self,
        task_id: str,
        target: str,
        reason: str,
        user_id: Optional[str] = None,
        accepted_by: Optional[str] = None,
        executor_type: Optional[str] = None,
        executor_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Apply an explicit transition; the caller enforces platform authorization."""
        if target == "ready" and self.registry is not None:
            from agno.company.execution import _executor

            _executor(self.registry, executor_type, executor_id, accepting=True)
        return await self.db.transition_task(
            task_id,
            target,
            reason,
            user_id=user_id,
            accepted_by=accepted_by,
            executor_type=executor_type,
            executor_id=executor_id,
        )

    async def start_task_run(
        self,
        task_id: str,
        attempt: int,
        expected_transitions: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        run_db_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Reserve accepted work; HTTP validates run authority before calling this method."""
        return await self.db.start_task_run(
            task_id, attempt, expected_transitions, user_id=user_id, run_db_id=run_db_id
        )

    async def complete_task_run(
        self,
        task_id: str,
        job_id: str,
        result: Dict[str, Any],
        expected_transitions: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Project the ordinary run result onto the current Task attempt."""
        return await self.db.complete_task_run(task_id, job_id, result, expected_transitions=expected_transitions)

    async def attention(self, product_id: Optional[str] = None) -> Dict[str, int]:
        """Company-wide counts over the same filters used by the Task list."""
        counts = {}
        for name, filters in (
            ("proposals", {"status": "backlog"}),
            ("in_review", {"status": "in_review"}),
            ("failed", {"failed": True}),
        ):
            _, counts[name] = await self.list_tasks(product_id=product_id, limit=1, **filters)
        return counts

    async def get_wiki(self, product_id: Optional[str] = None):
        """Return a Product or company wiki; reads are company-wide.

        Default pages are created atomically on first access and never reset.
        """
        from agno.company.playbook import _aseed, _wiki

        product = await self.get(product_id) if product_id is not None else None
        if product_id is not None and product is None:
            raise LookupError("Product not found")
        provider = _wiki(self.db, product)
        await _aseed(provider, product)
        return provider

    async def list_wiki(self, product_id: Optional[str] = None, limit: int = 20, page: int = 1):
        """List wiki pages with the standard Company pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        provider = await self.get_wiki(product_id)
        pages = await provider.backend.filesystem.alist()
        return pages[(page - 1) * limit : page * limit], len(pages)

    async def read_wiki(self, product_id: Optional[str], path: str):
        """Read a Markdown page and its filesystem version."""
        from agno.company.playbook import _page_path

        provider = await self.get_wiki(product_id)
        result = await provider.backend.filesystem.aread_with_meta(_page_path(path))
        if result is None:
            raise LookupError("Wiki page not found")
        return result

    async def write_wiki(
        self, product_id: Optional[str], path: str, content: str, expected_version: int, user_id: Optional[str] = None
    ):
        """Write with a filesystem version check; a scoped caller must own the Product.

        Company-wide pages are unowned, like shared components, and therefore
        editable only by unscoped callers. Version zero means create only.
        """
        from agno.company.playbook import _page_path, _require_owner

        if expected_version < 0:
            raise ValueError("expected_version must be nonnegative")
        product = await self.get(product_id) if product_id is not None else {}
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, user_id)
        provider = await self.get_wiki(product_id)
        return await provider.backend.filesystem.awrite(_page_path(path), content, expected_version=expected_version)

    async def log_decision(
        self,
        decision: str,
        reasoning: Optional[str] = None,
        context: Optional[str] = None,
        outcome: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ):
        """Append an owned entry to the learning decision log, never a wiki page."""
        from agno.company.decisions import CompanyDecisionLogStore, _new_decision

        entry = _new_decision(decision, reasoning, context, outcome, user_id, session_id, agent_id)
        await CompanyDecisionLogStore(self.db).asave(entry)
        return entry

    async def list_decisions(
        self,
        query: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 20,
        page: int = 1,
    ):
        """Search Company decisions across owners using the learning store's filters."""
        from agno.company.decisions import CompanyDecisionLogStore

        if limit < 1 or page < 1 or (days is not None and days < 1):
            raise ValueError("limit, page and days must be positive")
        entries = await CompanyDecisionLogStore(self.db).asearch(
            query=query, agent_id=agent_id, session_id=session_id, days=days, limit=None
        )
        return entries[(page - 1) * limit : page * limit], len(entries)
