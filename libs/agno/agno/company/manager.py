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

    def __init__(self, db: BaseDb, registry: Any = None, schedule_db: Any = None):
        self.db = db
        self.registry = registry
        self.schedule_db = schedule_db if schedule_db is not None else db

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
        record = self.db.get_product(product_id, user_id=user_id, include_deleted=include_deleted)
        if record is not None:
            record["counts"] = (self.db.get_product_counts([product_id]))[product_id]
        return record

    def list(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Return a page of visible Products and the total before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        rows, total = self.db.get_products(
            user_id=user_id,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        counts = self.db.get_product_counts([row["id"] for row in rows])
        return [{**row, "counts": counts[row["id"]]} for row in rows], total

    def update(self, product_id: str, user_id: Optional[str] = None, **fields: Any) -> Optional[Dict[str, Any]]:
        """Update name, purpose or metadata on an active Product."""
        validate_product_fields(fields)
        return self.db.update_product(product_id, user_id=user_id, **fields)

    def delete(self, product_id: str, user_id: Optional[str] = None) -> bool:
        """Archive a Product and its children atomically; active Tasks raise ValueError."""
        return self.db.delete_product(product_id, user_id=user_id)

    def restore(self, product_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a Product and only children archived by it; return None if already active."""
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
        record = self.db.get_project(project_id, user_id=user_id, include_deleted=include_deleted)
        if record is not None:
            record["counts"] = (self.db.get_project_counts([project_id]))[project_id]
        return record

    def list_projects(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
        product_id: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List across Products, filtering status and owner before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        rows, total = self.db.get_projects(
            user_id=user_id,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            product_id=product_id,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        counts = self.db.get_project_counts([row["id"] for row in rows])
        return [{**row, "counts": counts[row["id"]]} for row in rows], total

    def update_project(
        self, project_id: str, user_id: Optional[str] = None, expected_status: Optional[str] = None, **fields: Any
    ) -> Optional[Dict[str, Any]]:
        """Update the name, outcome or target date of a visible Project."""
        from agno.db.schemas.projects import validate_project_fields

        validate_project_fields(fields)
        if expected_status is not None:
            fields["expected_status"] = expected_status
        return self.db.update_project(project_id, user_id=user_id, **fields)

    def delete_project(
        self, project_id: str, user_id: Optional[str] = None, updated_before: Optional[int] = None
    ) -> bool:
        """Archive a Project and its Tasks atomically; active Tasks raise ValueError."""
        return self.db.delete_project(project_id, user_id=user_id, updated_before=updated_before)

    def restore_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a Project and only Tasks archived by it."""
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
        from agno.company.routines import _RoutineAuthorization
        from agno.db.schemas.projects import validate_project_completion
        from agno.run.authorization import current_authorization

        if isinstance(current_authorization(), _RoutineAuthorization):
            raise PermissionError("Routines propose Project completion; a human must accept the transition")
        if target == "done":
            page = 1
            while True:
                tasks, total = self.db.get_tasks(project_id=project_id, include_deleted=True, limit=100, page=page)
                validate_project_completion(tasks)
                if page * 100 >= total:
                    break
                page += 1
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
        origin: str = "human",
        routine_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create task work; scoped_user_id filters parents while user_id records the creator."""
        from agno.company.routines import _RoutineAuthorization
        from agno.run.authorization import current_authorization

        if isinstance(current_authorization(), _RoutineAuthorization):
            raise PermissionError(
                "Routines must propose Tasks through intake_company_source with evidence and a dedupe key"
            )
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
                "origin": origin,
                "routine_id": routine_id,
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
        session_id: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
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
            session_id=session_id,
            sort_by=sort_by,
            sort_order=sort_order,
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

    def delete_task(self, task_id: str, user_id: Optional[str] = None, updated_before: Optional[int] = None) -> bool:
        """Soft-delete a visible task."""
        return self.db.delete_task(task_id, user_id=user_id, updated_before=updated_before)

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
        from agno.company.routines import _RoutineAuthorization
        from agno.run.authorization import current_authorization

        if isinstance(current_authorization(), _RoutineAuthorization) and target in {"ready", "done"}:
            raise PermissionError("Routines can propose work but cannot accept or complete it")
        if target == "ready":
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

    def attention(self, product_id: Optional[str] = None) -> Dict[str, int]:
        """Company-wide counts over the same filters used by the Task list."""
        counts = {}
        for name, filters in (
            ("proposals", {"status": "backlog"}),
            ("in_review", {"status": "in_review"}),
            ("failed", {"failed": True}),
        ):
            _, counts[name] = self.list_tasks(product_id=product_id, limit=1, **filters)
        from agno.company.routines import _failed_routines

        products = []
        if product_id is not None:
            product = self.get(product_id)
            if product is not None:
                products.append(product)
        else:
            page = 1
            while True:
                rows, total = self.list(limit=100, page=page)
                products.extend(rows)
                if page * 100 >= total:
                    break
                page += 1
        counts["failed"] += _failed_routines(self.schedule_db, products)
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

    def create_source(
        self,
        product_id: str,
        type: str,
        reference: str,
        credential_ref: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        scoped_user_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Configure a reader on an owned Product; secret values are never resolved."""
        from agno.company.playbook import _require_owner
        from agno.db.schemas.sources import validate_source_fields

        fields = dict(type=type, reference=reference, credential_ref=credential_ref, config=config)
        validate_source_fields(fields)
        product = self.get(product_id)
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, scoped_user_id)
        return self.db.create_source(
            {
                **fields,
                "id": source_id or str(uuid4()),
                "product_id": product_id,
                "user_id": user_id,
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    def get_source(self, source_id: str, user_id: Optional[str] = None, include_deleted: bool = False):
        """Read a configured Source."""
        return self.db.get_source(source_id, user_id=user_id, include_deleted=include_deleted)

    def list_sources(
        self,
        product_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
    ):
        """List Sources using the database's paging and owner filters."""
        return self.db.get_sources(
            product_id=product_id, user_id=user_id, limit=limit, page=page, include_deleted=include_deleted
        )

    def delete_source(self, source_id: str, user_id: Optional[str] = None) -> bool:
        """Soft delete a Source after checking its Product ownership."""
        from agno.company.playbook import _require_owner

        source = self.get_source(source_id)
        if source is None:
            return False
        product = self.get(source["product_id"])
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, user_id)
        return self.db.delete_source(source_id)

    def restore_source(self, source_id: str, user_id: Optional[str] = None):
        """Restore a Source after checking its Product ownership."""
        from agno.company.playbook import _require_owner

        source = self.get_source(source_id, include_deleted=True)
        if source is None:
            return None
        product = self.get(source["product_id"])
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, user_id)
        return self.db.restore_source(source_id)

    def read_source(self, source_id: str, run_id: str, links: Optional[List[str]] = None):
        """Read the configured reader and attach this run's immutable evidence."""
        from agno.company.sources import read_source

        source = self.get_source(source_id)
        if source is None or self.get(source["product_id"]) is None:
            raise LookupError("Source not found")
        return read_source(source, run_id, links=links)

    def browse_source(
        self,
        source_id: str,
        run_id: str,
        path: Optional[str] = None,
        pattern: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
        content_offset: int = 0,
        max_chars: int = 8000,
    ):
        """Page Source discovery or read a bounded fragment with the full document's hash."""
        from agno.company.sources import browse_source

        source = self.get_source(source_id)
        if source is None or self.get(source["product_id"]) is None:
            raise LookupError("Source not found")
        return browse_source(source, run_id, path, pattern, offset, limit, content_offset, max_chars)

    def intake(
        self,
        source_id: str,
        run_id: str,
        proposal: Any,
        user_id: Optional[str] = None,
        routine_id: Optional[str] = None,
    ):
        """Persist an explicit proposal with verified evidence and a stable Source-local identity."""
        from agno.company.declarations import IntakeProposal
        from agno.company.sources import _proposal_fields

        source = self.get_source(source_id)
        if source is None:
            raise LookupError("Source not found")
        proposal = IntakeProposal.model_validate(proposal)
        evidence = self.read_source(source_id, run_id, links=proposal.evidence_links)
        fields = _proposal_fields(source_id, proposal, evidence)
        return self.db.create_task(
            {
                **fields,
                "id": str(uuid4()),
                "product_id": source["product_id"],
                "status": "backlog",
                "origin": "routine" if routine_id else "product_manager",
                "routine_id": routine_id,
                "session_id": str(uuid4()),
                "user_id": user_id,
                "transitions": [],
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    def refresh(self, product_id: str, user_id: Optional[str] = None):
        """Propose Project completion and apply the Product's archive window."""
        from agno.company.refresh import refresh_product

        return refresh_product(self, product_id, user_id)

    def summarize(self, product_id: str, run_id: str, interfaces: Any, narrative: str, user_id: Optional[str] = None):
        """Write the observed report to the wiki and deliver using Product configuration."""
        from agno.company.playbook import _require_owner
        from agno.company.summary import _summary_delivered, _summary_page, _summary_report, deliver_summary

        product = self.get(product_id)
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, user_id)
        delivery = (product.get("metadata") or {}).get("summary") or {}
        if not delivery.get("interface") or not delivery.get("destination"):
            raise ValueError("Product summary requires an interface and destination")
        counts = self.attention(product_id)
        rows = []
        page = 1
        while True:
            tasks, total = self.list_tasks(product_id=product_id, limit=100, page=page)
            rows.extend(tasks)
            if page * 100 >= total:
                break
            page += 1
        path = "summary.md"
        try:
            existing = self.read_wiki(product_id, path)
        except LookupError:
            existing = None
        content = _summary_report(product, counts, rows, narrative, existing.content if existing else "")
        report, delivered, marker = _summary_page(existing.content if existing else "", run_id, content)
        if delivered:
            return {"path": path, "delivered": True, "quiet": True}
        saved = self.write_wiki(product_id, path, report, existing.metadata.version if existing else 0, user_id=user_id)
        deliver_summary(
            interfaces,
            delivery["interface"],
            delivery["destination"],
            content.partition("\n\n<!-- Company summary snapshot:")[0],
        )
        self.write_wiki(product_id, path, _summary_delivered(report, marker), saved.version, user_id=user_id)
        return {"path": path, "delivered": True, "quiet": not rows}


class AsyncCompanyManager:
    """Manage Products through an asynchronous database.

    user_id=None leaves reads and writes unscoped; a string restricts them to
    that owner. On create it records the accountable owner.
    """

    def __init__(self, db: AsyncBaseDb, registry: Any = None, schedule_db: Any = None):
        self.db = db
        self.registry = registry
        self.schedule_db = schedule_db if schedule_db is not None else db

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
        record = await self.db.get_product(product_id, user_id=user_id, include_deleted=include_deleted)
        if record is not None:
            record["counts"] = (await self.db.get_product_counts([product_id]))[product_id]
        return record

    async def list(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Return a page of visible Products and the total before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        rows, total = await self.db.get_products(
            user_id=user_id,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        counts = await self.db.get_product_counts([row["id"] for row in rows])
        return [{**row, "counts": counts[row["id"]]} for row in rows], total

    async def update(self, product_id: str, user_id: Optional[str] = None, **fields: Any) -> Optional[Dict[str, Any]]:
        """Update name, purpose or metadata on an active Product."""
        validate_product_fields(fields)
        return await self.db.update_product(product_id, user_id=user_id, **fields)

    async def delete(self, product_id: str, user_id: Optional[str] = None) -> bool:
        """Archive a Product and its children atomically; active Tasks raise ValueError."""
        return await self.db.delete_product(product_id, user_id=user_id)

    async def restore(self, product_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a Product and only children archived by it; return None if already active."""
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
        record = await self.db.get_project(project_id, user_id=user_id, include_deleted=include_deleted)
        if record is not None:
            record["counts"] = (await self.db.get_project_counts([project_id]))[project_id]
        return record

    async def list_projects(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
        product_id: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List across Products, filtering status and owner before pagination."""
        if limit < 1 or page < 1:
            raise ValueError("limit and page must be positive")
        rows, total = await self.db.get_projects(
            user_id=user_id,
            limit=limit,
            page=page,
            include_deleted=include_deleted,
            product_id=product_id,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        counts = await self.db.get_project_counts([row["id"] for row in rows])
        return [{**row, "counts": counts[row["id"]]} for row in rows], total

    async def update_project(
        self, project_id: str, user_id: Optional[str] = None, expected_status: Optional[str] = None, **fields: Any
    ) -> Optional[Dict[str, Any]]:
        """Update the name, outcome or target date of a visible Project."""
        from agno.db.schemas.projects import validate_project_fields

        validate_project_fields(fields)
        if expected_status is not None:
            fields["expected_status"] = expected_status
        return await self.db.update_project(project_id, user_id=user_id, **fields)

    async def delete_project(
        self, project_id: str, user_id: Optional[str] = None, updated_before: Optional[int] = None
    ) -> bool:
        """Archive a Project and its Tasks atomically; active Tasks raise ValueError."""
        return await self.db.delete_project(project_id, user_id=user_id, updated_before=updated_before)

    async def restore_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Restore a Project and only Tasks archived by it."""
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
        from agno.company.routines import _RoutineAuthorization
        from agno.db.schemas.projects import validate_project_completion
        from agno.run.authorization import current_authorization

        if isinstance(current_authorization(), _RoutineAuthorization):
            raise PermissionError("Routines propose Project completion; a human must accept the transition")
        if target == "done":
            page = 1
            while True:
                tasks, total = await self.db.get_tasks(
                    project_id=project_id, include_deleted=True, limit=100, page=page
                )
                validate_project_completion(tasks)
                if page * 100 >= total:
                    break
                page += 1
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
        origin: str = "human",
        routine_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create task work; scoped_user_id filters parents while user_id records the creator."""
        from agno.company.routines import _RoutineAuthorization
        from agno.run.authorization import current_authorization

        if isinstance(current_authorization(), _RoutineAuthorization):
            raise PermissionError(
                "Routines must propose Tasks through intake_company_source with evidence and a dedupe key"
            )
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
                "origin": origin,
                "routine_id": routine_id,
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
        session_id: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
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
            session_id=session_id,
            sort_by=sort_by,
            sort_order=sort_order,
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

    async def delete_task(
        self, task_id: str, user_id: Optional[str] = None, updated_before: Optional[int] = None
    ) -> bool:
        """Soft-delete a visible task."""
        return await self.db.delete_task(task_id, user_id=user_id, updated_before=updated_before)

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
        from agno.company.routines import _RoutineAuthorization
        from agno.run.authorization import current_authorization

        if isinstance(current_authorization(), _RoutineAuthorization) and target in {"ready", "done"}:
            raise PermissionError("Routines can propose work but cannot accept or complete it")
        if target == "ready":
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

    async def attention(self, product_id: Optional[str] = None) -> Dict[str, int]:
        """Company-wide counts over the same filters used by the Task list."""
        counts = {}
        for name, filters in (
            ("proposals", {"status": "backlog"}),
            ("in_review", {"status": "in_review"}),
            ("failed", {"failed": True}),
        ):
            _, counts[name] = await self.list_tasks(product_id=product_id, limit=1, **filters)
        from agno.company.routines import _afailed_routines

        products = []
        if product_id is not None:
            product = await self.get(product_id)
            if product is not None:
                products.append(product)
        else:
            page = 1
            while True:
                rows, total = await self.list(limit=100, page=page)
                products.extend(rows)
                if page * 100 >= total:
                    break
                page += 1
        counts["failed"] += await _afailed_routines(self.schedule_db, products)
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

    async def create_source(
        self,
        product_id: str,
        type: str,
        reference: str,
        credential_ref: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        scoped_user_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Configure a reader on an owned Product; secret values are never resolved."""
        from agno.company.playbook import _require_owner
        from agno.db.schemas.sources import validate_source_fields

        fields = dict(type=type, reference=reference, credential_ref=credential_ref, config=config)
        validate_source_fields(fields)
        product = await self.get(product_id)
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, scoped_user_id)
        return await self.db.create_source(
            {
                **fields,
                "id": source_id or str(uuid4()),
                "product_id": product_id,
                "user_id": user_id,
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    async def get_source(self, source_id: str, user_id: Optional[str] = None, include_deleted: bool = False):
        """Read a configured Source."""
        return await self.db.get_source(source_id, user_id=user_id, include_deleted=include_deleted)

    async def list_sources(
        self,
        product_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
        include_deleted: bool = False,
    ):
        """List Sources using the database's paging and owner filters."""
        return await self.db.get_sources(
            product_id=product_id, user_id=user_id, limit=limit, page=page, include_deleted=include_deleted
        )

    async def delete_source(self, source_id: str, user_id: Optional[str] = None) -> bool:
        """Soft delete a Source after checking its Product ownership."""
        from agno.company.playbook import _require_owner

        source = await self.get_source(source_id)
        if source is None:
            return False
        product = await self.get(source["product_id"])
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, user_id)
        return await self.db.delete_source(source_id)

    async def restore_source(self, source_id: str, user_id: Optional[str] = None):
        """Restore a Source after checking its Product ownership."""
        from agno.company.playbook import _require_owner

        source = await self.get_source(source_id, include_deleted=True)
        if source is None:
            return None
        product = await self.get(source["product_id"])
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, user_id)
        return await self.db.restore_source(source_id)

    async def read_source(self, source_id: str, run_id: str, links: Optional[List[str]] = None):
        """Read the configured reader and attach this run's immutable evidence."""
        from agno.company.sources import aread_source

        source = await self.get_source(source_id)
        if source is None or await self.get(source["product_id"]) is None:
            raise LookupError("Source not found")
        return await aread_source(source, run_id, links=links)

    async def browse_source(
        self,
        source_id: str,
        run_id: str,
        path: Optional[str] = None,
        pattern: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
        content_offset: int = 0,
        max_chars: int = 8000,
    ):
        """Page Source discovery or read a bounded fragment with the full document's hash."""
        from agno.company.sources import abrowse_source

        source = await self.get_source(source_id)
        if source is None or await self.get(source["product_id"]) is None:
            raise LookupError("Source not found")
        return await abrowse_source(source, run_id, path, pattern, offset, limit, content_offset, max_chars)

    async def intake(
        self,
        source_id: str,
        run_id: str,
        proposal: Any,
        user_id: Optional[str] = None,
        routine_id: Optional[str] = None,
    ):
        """Persist an explicit proposal with verified evidence and a stable Source-local identity."""
        from agno.company.declarations import IntakeProposal
        from agno.company.sources import _proposal_fields

        source = await self.get_source(source_id)
        if source is None:
            raise LookupError("Source not found")
        proposal = IntakeProposal.model_validate(proposal)
        evidence = await self.read_source(source_id, run_id, links=proposal.evidence_links)
        fields = _proposal_fields(source_id, proposal, evidence)
        return await self.db.create_task(
            {
                **fields,
                "id": str(uuid4()),
                "product_id": source["product_id"],
                "status": "backlog",
                "origin": "routine" if routine_id else "product_manager",
                "routine_id": routine_id,
                "session_id": str(uuid4()),
                "user_id": user_id,
                "transitions": [],
                "created_at": int(time.time()),
                "updated_at": None,
                "deleted_at": None,
            }
        )

    async def refresh(self, product_id: str, user_id: Optional[str] = None):
        """Propose Project completion and apply the Product's archive window."""
        from agno.company.refresh import arefresh_product

        return await arefresh_product(self, product_id, user_id)

    async def summarize(
        self, product_id: str, run_id: str, interfaces: Any, narrative: str, user_id: Optional[str] = None
    ):
        """Write the observed report to the wiki and deliver using Product configuration."""
        from agno.company.playbook import _require_owner
        from agno.company.summary import _summary_delivered, _summary_page, _summary_report, adeliver_summary

        product = await self.get(product_id)
        if product is None:
            raise LookupError("Product not found")
        _require_owner(product, user_id)
        delivery = (product.get("metadata") or {}).get("summary") or {}
        if not delivery.get("interface") or not delivery.get("destination"):
            raise ValueError("Product summary requires an interface and destination")
        counts = await self.attention(product_id)
        rows = []
        page = 1
        while True:
            tasks, total = await self.list_tasks(product_id=product_id, limit=100, page=page)
            rows.extend(tasks)
            if page * 100 >= total:
                break
            page += 1
        path = "summary.md"
        try:
            existing = await self.read_wiki(product_id, path)
        except LookupError:
            existing = None
        content = _summary_report(product, counts, rows, narrative, existing.content if existing else "")
        report, delivered, marker = _summary_page(existing.content if existing else "", run_id, content)
        if delivered:
            return {"path": path, "delivered": True, "quiet": True}
        saved = await self.write_wiki(
            product_id, path, report, existing.metadata.version if existing else 0, user_id=user_id
        )
        await adeliver_summary(
            interfaces,
            delivery["interface"],
            delivery["destination"],
            content.partition("\n\n<!-- Company summary snapshot:")[0],
        )
        await self.write_wiki(product_id, path, _summary_delivered(report, marker), saved.version, user_id=user_id)
        return {"path": path, "delivered": True, "quiet": not rows}
