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

    def __init__(self, db: BaseDb):
        self.db = db

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

    def update_project(self, project_id: str, user_id: Optional[str] = None, **fields: Any) -> Optional[Dict[str, Any]]:
        """Update the name, outcome or target date of a visible Project."""
        from agno.db.schemas.projects import validate_project_fields

        validate_project_fields(fields)
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
    ) -> Dict[str, Any]:
        """Create task work; scoped_user_id filters parents while user_id records the creator."""
        from agno.db.schemas.tasks import validate_task_fields

        fields = {"title": title, "brief": brief, "project_id": project_id}
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
            project = self.db.get_project(fields["project_id"], user_id=user_id)
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
        return self.db.transition_task(
            task_id,
            target,
            reason,
            user_id=user_id,
            accepted_by=accepted_by,
            executor_type=executor_type,
            executor_id=executor_id,
        )


class AsyncCompanyManager:
    """Manage Products through an asynchronous database.

    user_id=None leaves reads and writes unscoped; a string restricts them to
    that owner. On create it records the accountable owner.
    """

    def __init__(self, db: AsyncBaseDb):
        self.db = db

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
        self, project_id: str, user_id: Optional[str] = None, **fields: Any
    ) -> Optional[Dict[str, Any]]:
        """Update the name, outcome or target date of a visible Project."""
        from agno.db.schemas.projects import validate_project_fields

        validate_project_fields(fields)
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
    ) -> Dict[str, Any]:
        """Create task work; scoped_user_id filters parents while user_id records the creator."""
        from agno.db.schemas.tasks import validate_task_fields

        fields = {"title": title, "brief": brief, "project_id": project_id}
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
            project = await self.db.get_project(fields["project_id"], user_id=user_id)
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
        return await self.db.transition_task(
            task_id,
            target,
            reason,
            user_id=user_id,
            accepted_by=accepted_by,
            executor_type=executor_type,
            executor_id=executor_id,
        )
