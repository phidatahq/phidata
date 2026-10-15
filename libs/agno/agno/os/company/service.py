"""Transactional Company records and human review. Every async method offloads one whole transaction."""

import asyncio
import base64
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from agno.os.company.config import CompanyConfig
from agno.os.company.migrations import VERSION
from agno.os.company.policy import CompanyError, Principal
from agno.os.company.schemas import (
    CommentCreate,
    CompanySetup,
    ListQuery,
    MemberCreate,
    MemberPatch,
    ProductCreate,
    ProductPatch,
    ProjectCreate,
    ProjectPatch,
    PullRequestReview,
    Reason,
    TaskCreate,
    TaskPatch,
    Transition,
)

_TABLES = {"product": "products", "project": "projects", "task": "tasks"}
_ROLES = {"reader": 0, "contributor": 1, "owner": 2}


if TYPE_CHECKING:
    from agno.agent import Agent


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _query(conn: Any, sql: str, **params: Any) -> Any:
    return conn.execute(text(sql), params)


def _row(conn: Any, sql: str, **params: Any) -> Optional[Dict[str, Any]]:
    result = _query(conn, sql, **params).mappings().first()
    return dict(result) if result else None


class CompanyService:
    def __init__(self, config: CompanyConfig, user_directory: Any = None):
        self._config = config
        self.product_manager: Optional["Agent"] = None
        self._engine = config.db.db_engine
        self._users = user_directory
        self._runtime: Any = None
        if user_directory is not None and getattr(user_directory, "_db_is_async", False):
            raise ValueError("Company requires a synchronous UserDirectory for its threaded transactions")

    @contextmanager
    def _transaction(self, principal: Principal, *, read: bool = False) -> Iterator[Any]:
        self._human(principal, principal.id)
        try:
            with (
                self._engine.connect().execution_options(
                    isolation_level="REPEATABLE READ" if read else "READ COMMITTED"
                ) as conn,
                conn.begin(),
            ):
                _query(conn, "SET LOCAL TIME ZONE 'UTC'")
                exists = _query(conn, "SELECT to_regclass('agno_company.schema_version')").scalar()
                if (
                    not exists
                    or _query(conn, "SELECT max(version) FROM agno_company.schema_version").scalar() != VERSION
                ):
                    raise CompanyError(503, "schema_required", "Apply Company migrations before serving this release")
                yield conn
        except IntegrityError as exc:
            raise CompanyError(
                409, "constraint_conflict", "The change conflicts with an existing record or reference"
            ) from exc
        except SQLAlchemyError as exc:
            raise CompanyError(
                503, "store_unavailable", "Company storage is unavailable; contact the operator"
            ) from exc

    def _human(self, principal: Principal, subject: str) -> None:
        from agno.os.middleware.jwt import is_reserved_principal

        if not subject or is_reserved_principal(subject) or subject.startswith(("agent:", "service:")):
            raise CompanyError(403, "human_required", "An active human identity is required")
        if self._users is None:
            if subject != principal.id:
                raise CompanyError(422, "unknown_principal", "Configure a UserDirectory to assign other known humans")
        else:
            try:
                user = self._users.get(subject)
            except Exception as exc:
                raise CompanyError(503, "identity_unavailable", "The identity directory is unavailable") from exc
            if not user or user.get("disabled") or (user.get("metadata") or {}).get("kind", "human") != "human":
                raise CompanyError(403, "inactive_principal", "An active known human identity is required")

    def _allowed(self, principal: Principal, action: str, product_id: Optional[str] = None) -> bool:
        if principal.agent_id and (
            action not in ("read", "write", "bootstrap")
            or (principal.product_id and product_id != principal.product_id)
        ):
            return False
        try:
            return principal.provider.check(principal.context(action, product_id))
        except Exception as exc:
            raise CompanyError(503, "policy_unavailable", "Company authorization is unavailable") from exc

    def _product(self, conn: Any, principal: Principal, product_id: str, *, lock: bool = False) -> Dict[str, Any]:
        product = _row(
            conn, "SELECT * FROM agno_company.products WHERE id=:id" + (" FOR UPDATE" if lock else ""), id=product_id
        )
        member = _row(
            conn,
            "SELECT role FROM agno_company.product_memberships WHERE product_id=:id AND principal_id=:who AND active",
            id=product_id,
            who=principal.id,
        )
        if not product or not member or not self._allowed(principal, "read", product_id):
            raise CompanyError(404, "not_found", "Record not found")
        product["role"] = member["role"]
        return product

    def _require(self, principal: Principal, product: Dict[str, Any], role: str, action: str) -> None:
        if _ROLES[product["role"]] < _ROLES[role] or not self._allowed(principal, action, str(product["id"])):
            raise CompanyError(403, "forbidden", "This action is not permitted")

    def _member(self, conn: Any, principal: Principal, product_id: str, subject: str) -> None:
        self._human(principal, subject)
        if not _query(
            conn,
            "SELECT 1 FROM agno_company.product_memberships WHERE product_id=:id AND principal_id=:who AND active",
            id=product_id,
            who=subject,
        ).scalar():
            raise CompanyError(
                409, "inactive_member", "The accountable human or assignee must be an active Product member"
            )

    def _load(self, conn: Any, principal: Principal, kind: str, record_id: str, *, lock: bool = False) -> Any:
        table = _TABLES[kind]
        record = _row(conn, f"SELECT * FROM agno_company.{table} WHERE id=:id", id=record_id)
        if not record:
            raise CompanyError(404, "not_found", "Record not found")
        product_id = str(record["id"] if kind == "product" else record["product_id"])
        product = self._product(conn, principal, product_id, lock=lock)
        # Reread after acquiring the shared Product lock: all mutations serialize on it.
        if lock:
            record = _row(conn, f"SELECT * FROM agno_company.{table} WHERE id=:id", id=record_id)
        return record, product

    def _counts(self, conn: Any, product_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        counts = _row(
            conn,
            """SELECT
            count(*) AS total_tasks,
            count(*) FILTER (WHERE accepted_at IS NOT NULL AND project_id IS NOT NULL) AS accepted_tasks,
            count(*) FILTER (WHERE status='done') AS done_tasks,
            count(*) FILTER (WHERE status='backlog') AS backlog,
            count(*) FILTER (WHERE status='ready') AS ready,
            count(*) FILTER (WHERE status='in_progress') AS in_progress,
            count(*) FILTER (WHERE status='in_review') AS in_review,
            transaction_timestamp() AS as_of FROM agno_company.tasks
            WHERE product_id=:pid AND state='active'"""
            + (" AND project_id=:project" if project_id else ""),
            pid=product_id,
            project=project_id,
        )
        assert counts is not None
        counts["active_projects"] = _query(
            conn,
            """SELECT count(*) FROM agno_company.projects p
            WHERE product_id=:pid AND state='active' AND
            (NOT EXISTS(SELECT 1 FROM agno_company.tasks t WHERE t.project_id=p.id AND t.state='active')
            OR EXISTS(SELECT 1 FROM agno_company.tasks t WHERE t.project_id=p.id AND t.state='active' AND t.status<>'done'))""",
            pid=product_id,
        ).scalar()
        return counts

    def _actions(
        self, conn: Any, principal: Principal, kind: str, record: Dict[str, Any], product: Dict[str, Any]
    ) -> list:
        pid = str(product["id"])
        owner = product["role"] == "owner"
        manage = owner and self._allowed(principal, "manage", pid)
        write = _ROLES[product["role"]] >= 1 and self._allowed(principal, "write", pid)
        review = owner and self._allowed(principal, "review", pid)
        if product["state"] == "archived":
            return ["restore"] if kind == "product" and manage else []
        if record["state"] == "archived":
            return ["restore"] if owner and write else []
        if kind == "product":
            return (
                (["edit", "archive", "members"] if manage else [])
                + (["create_project"] if owner and write else [])
                + (["create_task"] if write else [])
            )
        if kind == "project":
            return (["edit", "archive"] if owner and write else []) + (["create_task", "comment"] if write else [])
        if record.get("project_id"):
            parent = _row(conn, "SELECT state FROM agno_company.projects WHERE id=:id", id=record["project_id"])
            if parent and parent["state"] == "archived":
                return []
        status = record["status"]
        actions = ["edit", "comment"] if write and status not in ("in_review", "done") else []
        if owner and write:
            actions.append("archive")
        if status is None:
            return actions
        if status == "backlog" and review:
            actions.append("transition:ready")
        if write and status in ("ready", "in_progress"):
            actions.append("transition:" + ("in_progress" if status == "ready" else "in_review"))
        if review:
            if status == "in_review":
                actions += ["transition:done", "transition:in_progress", "link_pull_request"]
            if status in ("ready", "done"):
                actions.append("transition:backlog")
        return actions

    def _present(
        self, conn: Any, principal: Principal, kind: str, record: Dict[str, Any], product: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = dict(record)
        result.pop("role", None)
        # Older pilot stores may retain columns that are no longer part of the API.
        result.pop("legacy_status", None)
        if kind == "project":
            result.pop("completed_at", None)
        for private in ("schedule_principal", "ready_principal", "ready_agent_id", "review_principal"):
            result.pop(private, None)
        result["permitted_actions"] = self._actions(conn, principal, kind, record, product)
        if kind != "task":
            result["counts"] = self._counts(conn, str(product["id"]), str(record["id"]) if kind == "project" else None)
        if kind == "project":
            counts = result["counts"]
            result["status"] = (
                "empty"
                if not counts["total_tasks"]
                else ("completed" if counts["total_tasks"] == counts["done_tasks"] else "active")
            )
        if kind == "product":
            result["latest_activity_at"] = _query(
                conn, "SELECT max(created_at) FROM agno_company.activity WHERE product_id=:id", id=record["id"]
            ).scalar()
        return result

    def _get(self, principal: Principal, kind: str, record_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        with self._transaction(principal, read=True) as conn:
            record, product = self._load(conn, principal, kind, record_id)
            if project_id is not None and str(record.get("project_id")) != project_id:
                raise CompanyError(404, "not_found", "Task not found in this Project")
            return self._present(conn, principal, kind, record, product)

    def _list(self, principal: Principal, kind: str, query: ListQuery) -> Dict[str, Any]:
        filters = query.model_dump(mode="json", exclude={"cursor", "limit"})
        binding = hashlib.sha256(_json([principal.id, kind, filters]).encode()).hexdigest()
        after = None
        if query.cursor:
            try:
                cursor = json.loads(base64.urlsafe_b64decode(query.cursor))
                if cursor[0] != binding:
                    raise ValueError()
                after = (datetime.fromisoformat(cursor[1]), str(UUID(cursor[2])))
            except Exception as exc:
                raise CompanyError(422, "invalid_cursor", "Cursor does not match this query") from exc
        with self._transaction(principal, read=True) as conn:
            if query.product_id:
                self._product(conn, principal, str(query.product_id))
            if query.project_id:
                project, _ = self._load(conn, principal, "project", str(query.project_id))
                if query.product_id and str(project["product_id"]) != str(query.product_id):
                    raise CompanyError(404, "not_found", "Record not found")
            table = _TABLES.get(kind, "activity")
            pid_column = "r.id" if kind == "product" else "r.product_id"
            clauses = [
                f"EXISTS (SELECT 1 FROM agno_company.product_memberships m WHERE m.product_id={pid_column} AND m.principal_id=:who AND m.active)"
            ]
            params: Dict[str, Any] = {"who": principal.id}
            for name in ("product_id", "project_id", "status", "owner_id", "assignee_id", "subject_type", "subject_id"):
                value = getattr(query, name)
                allowed = {
                    "product": set(),
                    "project": {"product_id", "owner_id"},
                    "task": {"product_id", "project_id", "status", "assignee_id"},
                    "activity": {"product_id", "subject_type", "subject_id"},
                }[kind]
                if value is not None and name in allowed:
                    clauses.append(f"r.{name}=:{name}")
                    params[name] = str(value)
            if query.key is not None and kind != "activity":
                clauses.append("r.key=:record_key")
                params["record_key"] = query.key
            if kind != "activity" and query.state != "all":
                clauses.append("r.state=:state")
                params["state"] = query.state or "active"
            if query.direct and kind == "task":
                clauses.append("r.project_id IS NULL")
            results: list[Dict[str, Any]] = []
            # Fetch bounded windows, applying provider policy before output pagination.
            # This also honors custom providers that deny individual ids within a wildcard.
            while len(results) <= query.limit:
                window = list(clauses)
                if after:
                    window.append("(r.created_at,r.id) > (:after_time,:after_id)")
                    params.update(after_time=after[0], after_id=after[1])
                rows = (
                    _query(
                        conn,
                        f"SELECT r.* FROM agno_company.{table} r WHERE "
                        + " AND ".join(window)
                        + " ORDER BY r.created_at,r.id LIMIT 100",
                        **params,
                    )
                    .mappings()
                    .all()
                )
                if not rows:
                    break
                for row in rows:
                    record = dict(row)
                    after = (record["created_at"], str(record["id"]))
                    pid = str(record["id"] if kind == "product" else record["product_id"])
                    if kind == "project" and query.status:
                        counts = self._counts(conn, pid, str(record["id"]))
                        status = (
                            "empty"
                            if not counts["total_tasks"]
                            else ("completed" if counts["done_tasks"] == counts["total_tasks"] else "active")
                        )
                        if status != query.status:
                            continue
                    if not self._allowed(principal, "read", pid):
                        continue
                    product = self._product(conn, principal, pid)
                    results.append(
                        record if kind == "activity" else self._present(conn, principal, kind, record, product)
                    )
                    if len(results) > query.limit:
                        break
                if len(rows) < 100:
                    break
            next_cursor = None
            if len(results) > query.limit:
                results = results[: query.limit]
                last = results[-1]
                next_cursor = base64.urlsafe_b64encode(
                    _json([binding, last["created_at"].isoformat(), str(last["id"])]).encode()
                ).decode()
            return {"data": results, "next_cursor": next_cursor}

    def _mutate(
        self,
        *,
        principal: Principal,
        kind: str,
        action: str,
        data: BaseModel,
        request_id: str,
        idempotency_key: str,
        record_id: Optional[str] = None,
        product_id: Optional[str] = None,
        version: Optional[int] = None,
        member_id: Optional[str] = None,
        _builtin: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not 1 <= len(idempotency_key) <= 200 or not 1 <= len(request_id) <= 200:
            raise CompanyError(
                422, "invalid_request_id", "Request and idempotency identifiers must be 1-200 characters"
            )
        body = data.model_dump(mode="json", exclude_unset=action == "edit")
        if (
            principal.agent_id
            and kind == "product"
            and (
                action != "create"
                or body.get("owner_id") not in (None, principal.id)
                or body.get("agent_id")
                or body.get("repository")
                or _builtin
            )
        ):
            raise CompanyError(
                403,
                "human_required",
                "Agents may create Products for the initiating human without selecting execution authority",
            )
        if principal.agent_id and (action not in ("create", "edit", "comment", "summary")):
            raise CompanyError(403, "human_required", "This management or review action requires a human")
        operation = "product.setup" if _builtin else f"{kind}.{action}"
        payload_hash = hashlib.sha256(_json([record_id, product_id, member_id, version, body]).encode()).hexdigest()
        with self._transaction(principal) as conn:
            if _builtin:
                if not self._allowed(principal, "bootstrap"):
                    raise CompanyError(403, "forbidden", "Company administration is required for setup")
                _query(conn, "SELECT pg_advisory_xact_lock(741927104)")
                existing = _row(conn, "SELECT * FROM agno_company.products WHERE builtin=:builtin", builtin=_builtin)
                if existing:
                    existing_product = self._product(conn, principal, str(existing["id"]))
                    return json.loads(_json(self._present(conn, principal, "product", existing, existing_product)))
            lock_key = int.from_bytes(
                hashlib.sha256(_json([principal.id, operation, idempotency_key]).encode()).digest()[:8],
                "big",
                signed=True,
            )
            _query(conn, "SELECT pg_advisory_xact_lock(:key)", key=lock_key)
            product: Any = None
            record: Any = None
            member: Optional[Dict[str, Any]] = None
            if kind == "product" and action == "create":
                if not self._allowed(principal, "bootstrap"):
                    raise CompanyError(403, "forbidden", "Company administration is required to create Products")
            elif record_id:
                record, product = self._load(conn, principal, kind, record_id, lock=True)
                product_id = str(product["id"])
            else:
                assert product_id is not None
                product = self._product(conn, principal, product_id, lock=True)
            replay = _row(
                conn,
                "SELECT * FROM agno_company.idempotency WHERE principal_id=:who AND operation=:op AND key=:key AND expires_at>now()",
                who=principal.id,
                op=operation,
                key=idempotency_key,
            )
            role, permission = "reader", "read"
            if product:
                role, permission = ("contributor", "write")
                if kind == "product" or action in ("member_create", "member_edit"):
                    role, permission = "owner", "manage"
                elif kind == "project":
                    role = "owner" if action not in ("comment", "summary") else "contributor"
                if action in ("archive", "restore", "schedule"):
                    role = "owner"
                    if action == "schedule":
                        permission = "manage"
                if action == "pull_request":
                    role, permission = "owner", "review"
                if action == "transition":
                    if (
                        kind == "project"
                        or body["to_status"] not in ("in_progress", "in_review")
                        or record["status"] == "in_review"
                    ):
                        role, permission = "owner", "review"
                if replay:
                    role, permission = replay["required_role"], replay["required_action"]
                self._require(principal, product, role, permission)
            if replay:
                if replay["payload_hash"] != payload_hash:
                    raise CompanyError(
                        409, "idempotency_mismatch", "This idempotency key was used with a different request"
                    )
                if kind == "product" and action == "create":
                    self._product(conn, principal, replay["result"]["id"])
                return replay["result"]
            if action not in ("create", "comment"):
                if version is None:
                    raise CompanyError(428, "precondition_required", "If-Match is required")
                assert record is not None
                if version != record["version"]:
                    raise CompanyError(412, "version_conflict", "The record changed; reload and reconcile your edits")
            if product and product["state"] == "archived" and action != "restore":
                raise CompanyError(409, "archived_parent", "Restore the Product before changing its records")
            if record and kind in ("task", "project"):
                if kind == "task" and record.get("project_id"):
                    parent = _row(conn, "SELECT state FROM agno_company.projects WHERE id=:id", id=record["project_id"])
                    if parent and parent["state"] == "archived":
                        raise CompanyError(409, "closed_parent", "Reopen the Project before changing its Tasks")
                if record["state"] == "archived" and action != "restore":
                    raise CompanyError(409, "archived_record", "Restore the record before changing it")
                if record.get("status") == "done" and action not in ("transition", "archive"):
                    raise CompanyError(409, "closed_record", "Reopen the record before editing or commenting")
            if action != "create":
                assert record_id is not None and record is not None and product is not None
            if (
                principal.agent_id
                and action == "edit"
                and (
                    kind != "task"
                    or record.get("status") not in (None, "backlog")
                    or {"agent_id", "accountable_owner_id", "assignee_id"}.intersection(body)
                )
            ):
                raise CompanyError(
                    403, "draft_only", "Agents can edit draft work, not accepted instructions or authority"
                )
            if kind == "task" and record and action in ("edit", "transition"):
                active = _query(
                    conn, "SELECT 1 FROM agno_company.task_runs WHERE task_id=:id AND NOT released", id=record_id
                ).scalar()
                if active:
                    raise CompanyError(409, "run_active", "Stop or finish the active run before changing the Task")
            if kind == "product" and action == "edit" and "repository" in body:
                if _query(
                    conn,
                    "SELECT 1 FROM agno_company.tasks WHERE product_id=:id AND status IN ('ready','in_progress','in_review') LIMIT 1",
                    id=record_id,
                ).scalar():
                    raise CompanyError(
                        409,
                        "work_active",
                        "Finish or return accepted Tasks to Backlog before changing their repository",
                    )
            if body.get("agent_id"):
                if self._runtime is None:
                    raise CompanyError(409, "worker_required", "Configure a registered AgentOS worker first")
                self._runtime._agent(principal, body["agent_id"])
            before = (
                {
                    k: v
                    for k, v in record.items()
                    if k not in ("schedule_principal", "ready_principal", "ready_agent_id", "review_principal")
                }
                if record
                else None
            )
            if action == "create":
                record_id = str(uuid4())
                values = {
                    **body,
                    "id": record_id,
                    "key": {"product": "PRD", "project": "PRJ", "task": "TSK"}[kind]
                    + "-"
                    + str(_query(conn, "SELECT nextval('agno_company.record_keys')").scalar()),
                }
                if kind == "product":
                    if _builtin:
                        values["builtin"] = _builtin
                    values["owner_id"] = body["owner_id"] or principal.id
                    self._human(principal, values["owner_id"])
                else:
                    assert product_id is not None
                    values["product_id"] = product_id
                    if kind == "project":
                        values["owner_id"] = body["owner_id"] or product["owner_id"]
                    if kind == "task":
                        values["origin"] = "agent" if principal.agent_id else "human"
                        values["status"] = "backlog" if body.get("project_id") else None
                        values["accountable_owner_id"] = body["accountable_owner_id"] or product["owner_id"]
                    if kind == "task" and body.get("project_id"):
                        parent = _row(
                            conn,
                            "SELECT * FROM agno_company.projects WHERE id=:id AND product_id=:pid",
                            id=body["project_id"],
                            pid=product_id,
                        )
                        if not parent or parent["state"] == "archived":
                            raise CompanyError(
                                409, "invalid_parent", "Task requires an open Project in the same Product"
                            )
                        values["accountable_owner_id"] = body["accountable_owner_id"] or parent["owner_id"]
                    for name in ("owner_id", "accountable_owner_id", "assignee_id"):
                        if values.get(name):
                            self._member(conn, principal, product_id, values[name])
                record = self._insert(conn, _TABLES[kind], values)
                if kind == "product":
                    product_id = record_id
                    self._insert(
                        conn,
                        "product_memberships",
                        {"product_id": product_id, "principal_id": values["owner_id"], "role": "owner"},
                    )
                    # Bootstrap callers need not become a member of another person's Product.
                    product = {**record, "role": "owner" if principal.id == values["owner_id"] else "reader"}
            elif action == "edit":
                assert record is not None and product is not None and product_id is not None and record_id is not None
                for name in ("owner_id", "accountable_owner_id", "assignee_id"):
                    if body.get(name):
                        self._member(conn, principal, product_id, body[name])
                if kind == "task":
                    protected = {"instructions", "evidence", "accountable_owner_id", "project_id"}.intersection(body)
                    if protected and record["status"] in ("in_review", "done"):
                        raise CompanyError(
                            409, "review_locked", "Return or reopen the Task before changing accepted scope or evidence"
                        )
                    if body.get("project_id"):
                        parent = _row(
                            conn,
                            "SELECT state FROM agno_company.projects WHERE id=:id AND product_id=:pid",
                            id=body["project_id"],
                            pid=product_id,
                        )
                        if not parent or parent["state"] == "archived":
                            raise CompanyError(
                                409, "invalid_parent", "Task requires an open Project in the same Product"
                            )
                    if record["accepted_at"] and {
                        "instructions",
                        "accountable_owner_id",
                        "project_id",
                    }.intersection(body):
                        role, permission = "owner", "review"
                        self._require(principal, product, role, permission)
                        if not body.get("instructions", record["instructions"]):
                            raise CompanyError(409, "criteria_required", "Accepted work requires instructions")
                    if "project_id" in body and str(body["project_id"]) != str(record["project_id"]):
                        if (record.get("schedule") or {}).get("enabled"):
                            raise CompanyError(409, "schedule_active", "Pause the recurring task before grouping it")
                        if record["status"] in ("in_progress", "in_review"):
                            raise CompanyError(409, "work_active", "Finish the active work before regrouping it")
                        body.update(
                            status="backlog" if body["project_id"] else None,
                            accepted_at=None,
                            accepted_by=None,
                            ready_principal=None,
                            ready_agent_id=None,
                            completed_at=None,
                        )
                if (
                    kind == "task"
                    and record["status"] == "ready"
                    and {"instructions", "agent_id", "accountable_owner_id"}.intersection(body)
                ):
                    self._require(principal, product, "owner", "review")
                    body.update(
                        status="backlog",
                        accepted_by=None,
                        accepted_at=None,
                        ready_principal=None,
                        ready_agent_id=None,
                        automation_error=None,
                    )
                record = self._update(conn, _TABLES[kind], record_id, body)
            elif action in ("archive", "restore"):
                assert record_id is not None
                desired = "archived" if action == "archive" else "active"
                if record["state"] == desired:
                    raise CompanyError(409, "invalid_transition", "Product is already in that state")
                record = self._update(conn, _TABLES[kind], record_id, {"state": desired})
                if kind == "product":
                    product = {**record, "role": product["role"]}
            elif action == "transition":
                assert record_id is not None
                changes = self._transition(conn, principal, kind, record, product, body)
                record = self._update(conn, _TABLES[kind], record_id, changes)
            elif action in ("member_create", "member_edit"):
                assert product is not None and record_id is not None
                member_id = member_id or body["principal_id"]
                if action == "member_create" or body["active"]:
                    self._human(principal, member_id)
                if member_id == product["owner_id"] and (body["role"] != "owner" or not body.get("active", True)):
                    raise CompanyError(
                        409, "owner_required", "The accountable Product owner cannot be demoted or removed"
                    )
                if not body.get("active", True):
                    active_refs = _query(
                        conn,
                        """SELECT EXISTS(SELECT 1 FROM agno_company.projects WHERE product_id=:pid AND owner_id=:who AND state='active')
                      OR EXISTS(SELECT 1 FROM agno_company.tasks WHERE product_id=:pid AND (accountable_owner_id=:who OR assignee_id=:who) AND state='active' AND (status IS NULL OR status<>'done'))""",
                        pid=product_id,
                        who=member_id,
                    ).scalar()
                    if active_refs:
                        raise CompanyError(
                            409, "active_reference", "Reassign active work before deactivating this member"
                        )
                if action == "member_create":
                    member = self._insert(conn, "product_memberships", {"product_id": product_id, **body})
                else:
                    member = _row(
                        conn,
                        "UPDATE agno_company.product_memberships SET role=:role,active=:active WHERE product_id=:pid AND principal_id=:who RETURNING *",
                        role=body["role"],
                        active=body["active"],
                        pid=product_id,
                        who=member_id,
                    )
                    if not member:
                        raise CompanyError(404, "not_found", "Membership not found")
                record = self._update(conn, "products", record_id, {})
                result = {**member, "version": record["version"]}
            elif action == "pull_request":
                assert record_id is not None
                if kind != "task" or record["status"] != "in_review":
                    raise CompanyError(409, "review_required", "Link a pull request while the Task is In review")
                if self._runtime is None:
                    raise CompanyError(409, "runtime_required", "Configure AgentOS to verify pull requests")
                record = self._update(
                    conn,
                    "tasks",
                    record_id,
                    {
                        "review_pull_request": body,
                        "review_principal": self._runtime._saved(principal),
                        "automation_error": None,
                    },
                )
            elif action == "schedule":
                assert record_id is not None
                if record["project_id"] and body["enabled"]:
                    raise CompanyError(409, "direct_task_required", "Only direct Product Tasks can recur")
                self._runtime._agent(principal, record["agent_id"] or product["agent_id"])
                saved = record["schedule_principal"] or self._runtime._saved(principal)
                if saved["id"] != principal.id:
                    raise CompanyError(
                        409, "schedule_owner", "Only the schedule owner can change its execution authority"
                    )
                record = self._update(
                    conn, "tasks", record_id, {"schedule": body, "schedule_principal": self._runtime._saved(principal)}
                )
            elif action == "summary":
                assert record_id is not None
                sources = {
                    str(row["id"]): row["version"]
                    for row in _query(
                        conn,
                        "SELECT id,version FROM agno_company.tasks WHERE project_id=:id AND state='active'",
                        id=record_id,
                    ).mappings()
                }
                if sources != body["source_versions"]:
                    raise CompanyError(412, "stale_summary", "Tasks changed; refresh the summary sources")
                record = self._update(
                    conn,
                    "projects",
                    record_id,
                    {"summary": body["summary"], "summary_at": datetime.now(timezone.utc), "summary_sources": sources},
                )
            elif action == "comment":
                result = self._insert(
                    conn,
                    "comments",
                    {
                        "id": str(uuid4()),
                        f"{kind}_id": record_id,
                        "author_id": principal.agent_id or principal.id,
                        "body": body["body"],
                    },
                )
            else:
                raise ValueError("Unknown Company mutation")
            assert record is not None and product is not None
            self._insert(
                conn,
                "activity",
                {
                    "id": str(uuid4()),
                    "product_id": product_id,
                    "subject_type": kind,
                    "subject_id": record_id,
                    "actor_id": principal.agent_id or principal.id,
                    "initiating_principal_id": principal.id,
                    "operation": operation,
                    "delta": {
                        "request": body,
                        "before": before,
                        "after": {
                            k: v
                            for k, v in record.items()
                            if k not in ("schedule_principal", "ready_principal", "ready_agent_id", "review_principal")
                        },
                        "member_id": member_id,
                    },
                    "request_id": request_id,
                },
            )
            if action not in ("member_create", "member_edit", "comment"):
                result = self._present(conn, principal, kind, record, product)
            result = json.loads(_json(result))
            _query(
                conn,
                "DELETE FROM agno_company.idempotency WHERE principal_id=:who AND operation=:op AND key=:key",
                who=principal.id,
                op=operation,
                key=idempotency_key,
            )
            self._insert(
                conn,
                "idempotency",
                {
                    "principal_id": principal.id,
                    "operation": operation,
                    "key": idempotency_key,
                    "payload_hash": payload_hash,
                    "required_role": role,
                    "required_action": permission,
                    "result": result,
                },
            )
            return result

    def _insert(self, conn: Any, table: str, values: Dict[str, Any]) -> Dict[str, Any]:
        expressions = [
            f"CAST(:{key} AS jsonb)" if key in ("evidence", "delta", "result", "repository") else f":{key}"
            for key in values
        ]
        params = {
            key: _json(value) if key in ("evidence", "delta", "result", "repository") else value
            for key, value in values.items()
        }
        result = _row(
            conn,
            f"INSERT INTO agno_company.{table} ({','.join(values)}) VALUES ({','.join(expressions)}) RETURNING *",
            **params,
        )
        assert result is not None
        return result

    def _update(self, conn: Any, table: str, record_id: str, values: Dict[str, Any]) -> Dict[str, Any]:
        fields = [
            f"{key}="
            + (
                f"CAST(:{key} AS jsonb)"
                if key
                in (
                    "evidence",
                    "summary_sources",
                    "repository",
                    "source",
                    "schedule",
                    "schedule_principal",
                    "ready_principal",
                    "review_principal",
                    "review_pull_request",
                )
                else f":{key}"
            )
            for key in values
        ]
        params = {
            key: _json(value)
            if value is not None
            and key
            in (
                "evidence",
                "summary_sources",
                "repository",
                "source",
                "schedule",
                "schedule_principal",
                "ready_principal",
                "review_principal",
                "review_pull_request",
            )
            else value
            for key, value in values.items()
        }
        fields += ["version=version+1", "updated_at=clock_timestamp()"]
        result = _row(
            conn, f"UPDATE agno_company.{table} SET {','.join(fields)} WHERE id=:id RETURNING *", id=record_id, **params
        )
        assert result is not None
        return result

    def _transition(
        self,
        conn: Any,
        principal: Principal,
        kind: str,
        record: Dict[str, Any],
        product: Dict[str, Any],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        target, status = body["to_status"], record["status"]
        if "transition:" + target not in self._actions(conn, principal, kind, record, product):
            raise CompanyError(409, "invalid_transition", "This transition is not available from the current state")
        changes: Dict[str, Any] = {"status": target}
        if not body["reason"] and (target in ("backlog", "done") or status == "in_review"):
            raise CompanyError(409, "reason_required", "Supply a reason or outcome assessment")
        if kind == "task":
            if target == "ready":
                if not record["instructions"] or not record["accountable_owner_id"]:
                    raise CompanyError(
                        409, "acceptance_required", "Ready requires instructions and an accountable human"
                    )
                self._member(conn, principal, str(product["id"]), record["accountable_owner_id"])
                changes.update(accepted_by=principal.id, accepted_at=datetime.now(timezone.utc))
                if product.get("repository"):
                    if self._runtime is None:
                        raise CompanyError(
                            409,
                            "worker_required",
                            "Configure a sandboxed Product Engineer before accepting repository work",
                        )
                    agent = self._runtime._agent(principal, record["agent_id"] or product["agent_id"])
                    self._runtime._require_engineer(agent)
                    changes["source"] = self._runtime._source(conn, product, record)
                if self._runtime is not None:
                    changes.update(
                        ready_principal=self._runtime._saved(principal),
                        ready_agent_id=record["agent_id"] or product["agent_id"],
                    )
            changes["automation_error"] = None
            if target == "in_review":
                changes["review_started_at"] = datetime.now(timezone.utc)
            else:
                changes.update(review_pull_request=None, review_principal=None, review_started_at=None)
            if target != "ready":
                changes.update(ready_principal=None, ready_agent_id=None)
            if target == "backlog":
                changes.update(accepted_by=None, accepted_at=None, completed_at=None)
            if target == "done":
                if not body["evidence"] and not record["evidence"] and not body["acceptance_check"]:
                    raise CompanyError(409, "review_required", "Supply evidence or explain how acceptance was checked")
                changes["completed_at"] = datetime.now(timezone.utc)
        if kind == "task" and body["evidence"]:
            changes["evidence"] = record["evidence"] + body["evidence"]
            if len(changes["evidence"]) > 20:
                raise CompanyError(422, "too_much_evidence", "A Task supports at most 20 evidence links")
        return changes

    def get_me(self, *, principal: Principal) -> Dict[str, Any]:
        self._human(principal, principal.id)
        bootstrap = self._allowed(principal, "bootstrap")
        page = self.list_products(principal=principal, query=ListQuery(limit=1, state="all"))
        return {
            "principal_id": principal.id,
            "company_access": bootstrap or bool(page["data"]),
            "permitted_actions": ["create_product"] if bootstrap else [],
        }

    async def aget_me(self, *, principal: Principal) -> Dict[str, Any]:
        return await asyncio.to_thread(self.get_me, principal=principal)

    def list_members(
        self, *, principal: Principal, product_id: str, query: Optional[ListQuery] = None
    ) -> Dict[str, Any]:
        query = query or ListQuery()
        with self._transaction(principal, read=True) as conn:
            product = self._product(conn, principal, product_id)
            self._require(principal, product, "owner", "manage")
            # Membership ids are strings rather than UUIDs. Bind the cursor to its Product.
            after = ""
            if query.cursor:
                try:
                    pid, who, after = json.loads(base64.urlsafe_b64decode(query.cursor))
                    if pid != product_id or who != principal.id:
                        raise ValueError()
                except Exception as exc:
                    raise CompanyError(422, "invalid_cursor", "Invalid membership cursor") from exc
            rows = [
                dict(row)
                for row in _query(
                    conn,
                    "SELECT *, :version AS version FROM agno_company.product_memberships WHERE product_id=:pid AND principal_id>:after ORDER BY principal_id LIMIT :limit",
                    version=product["version"],
                    pid=product_id,
                    after=after,
                    limit=query.limit + 1,
                ).mappings()
            ]
            cursor = (
                base64.urlsafe_b64encode(
                    _json([product_id, principal.id, rows[query.limit - 1]["principal_id"]]).encode()
                ).decode()
                if len(rows) > query.limit
                else None
            )
            return {"data": rows[: query.limit], "next_cursor": cursor}

    async def alist_members(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list_members, **kwargs)

    def list_comments(
        self, *, principal: Principal, kind: str, record_id: str, query: Optional[ListQuery] = None
    ) -> Dict[str, Any]:
        if kind not in ("project", "task"):
            raise ValueError("Comments require a Project or Task")
        query = query or ListQuery()
        with self._transaction(principal, read=True) as conn:
            self._load(conn, principal, kind, record_id)
            after_time, after_id = datetime.min.replace(tzinfo=timezone.utc), str(UUID(int=0))
            if query.cursor:
                try:
                    target, who, ts, uid = json.loads(base64.urlsafe_b64decode(query.cursor))
                    if target != f"{kind}:{record_id}" or who != principal.id:
                        raise ValueError()
                    after_time, after_id = datetime.fromisoformat(ts), str(UUID(uid))
                except Exception as exc:
                    raise CompanyError(422, "invalid_cursor", "Invalid comment cursor") from exc
            rows = [
                dict(row)
                for row in _query(
                    conn,
                    f"SELECT * FROM agno_company.comments WHERE {kind}_id=:id AND (created_at,id)>(:ts,:uid) ORDER BY created_at,id LIMIT :limit",
                    id=record_id,
                    ts=after_time,
                    uid=after_id,
                    limit=query.limit + 1,
                ).mappings()
            ]
            cursor = None
            if len(rows) > query.limit:
                last = rows[query.limit - 1]
                cursor = base64.urlsafe_b64encode(
                    _json(
                        [f"{kind}:{record_id}", principal.id, last["created_at"].isoformat(), str(last["id"])]
                    ).encode()
                ).decode()
            return {"data": rows[: query.limit], "next_cursor": cursor}

    async def alist_comments(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list_comments, **kwargs)

    def get_product(self, *, principal: Principal, product_id: str) -> Dict[str, Any]:
        return self._get(principal, "product", product_id)

    async def aget_product(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.get_product, **kwargs)

    def get_project(self, *, principal: Principal, project_id: str) -> Dict[str, Any]:
        return self._get(principal, "project", project_id)

    async def aget_project(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.get_project, **kwargs)

    def get_task(self, *, principal: Principal, task_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        return self._get(principal, "task", task_id, project_id)

    async def aget_task(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.get_task, **kwargs)

    def list_products(self, *, principal: Principal, query: Optional[ListQuery] = None) -> Dict[str, Any]:
        return self._list(principal, "product", query or ListQuery())

    async def alist_products(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list_products, **kwargs)

    def list_projects(self, *, principal: Principal, query: Optional[ListQuery] = None) -> Dict[str, Any]:
        return self._list(principal, "project", query or ListQuery())

    async def alist_projects(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list_projects, **kwargs)

    def list_tasks(self, *, principal: Principal, query: Optional[ListQuery] = None) -> Dict[str, Any]:
        return self._list(principal, "task", query or ListQuery())

    async def alist_tasks(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list_tasks, **kwargs)

    def list_activity(self, *, principal: Principal, query: Optional[ListQuery] = None) -> Dict[str, Any]:
        return self._list(principal, "activity", query or ListQuery())

    async def alist_activity(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list_activity, **kwargs)

    def setup_agentos(
        self, *, principal: Principal, data: CompanySetup, request_id: str, idempotency_key: str
    ) -> Dict[str, Any]:
        """Create the default AgentOS Product once during authenticated setup."""
        if principal.agent_id:
            raise CompanyError(403, "human_required", "Company setup requires a human")
        return self._mutate(
            principal=principal,
            kind="product",
            action="create",
            _builtin="agentos",
            data=ProductCreate(
                name="AgentOS",
                instructions="Develop and maintain this AgentOS application. Keep changes small, test them, and present results for human review.",
                **data.model_dump(),
            ),
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    async def asetup_agentos(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.setup_agentos, **kwargs)

    def create_product(
        self, *, principal: Principal, data: ProductCreate, request_id: str, idempotency_key: str
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="product",
            action="create",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    async def acreate_product(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.create_product, **kwargs)

    def update_product(
        self,
        *,
        principal: Principal,
        data: ProductPatch,
        request_id: str,
        idempotency_key: str,
        product_id: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="product",
            action="edit",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=product_id,
            version=version,
        )

    async def aupdate_product(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.update_product, **kwargs)

    def archive_product(
        self,
        *,
        principal: Principal,
        data: Reason,
        request_id: str,
        idempotency_key: str,
        product_id: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="product",
            action="archive",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=product_id,
            version=version,
        )

    async def aarchive_product(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.archive_product, **kwargs)

    def restore_product(
        self,
        *,
        principal: Principal,
        data: Reason,
        request_id: str,
        idempotency_key: str,
        product_id: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="product",
            action="restore",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=product_id,
            version=version,
        )

    async def arestore_product(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.restore_product, **kwargs)

    def add_member(
        self,
        *,
        principal: Principal,
        data: MemberCreate,
        request_id: str,
        idempotency_key: str,
        product_id: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="product",
            action="member_create",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=product_id,
            version=version,
        )

    async def aadd_member(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.add_member, **kwargs)

    def update_member(
        self,
        *,
        principal: Principal,
        data: MemberPatch,
        request_id: str,
        idempotency_key: str,
        product_id: str,
        version: Optional[int] = None,
        member_id: str,
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="product",
            action="member_edit",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=product_id,
            version=version,
            member_id=member_id,
        )

    async def aupdate_member(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.update_member, **kwargs)

    def create_project(
        self, *, principal: Principal, data: ProjectCreate, request_id: str, idempotency_key: str, product_id: str
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="project",
            action="create",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            product_id=product_id,
        )

    async def acreate_project(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.create_project, **kwargs)

    def update_project(
        self,
        *,
        principal: Principal,
        data: ProjectPatch,
        request_id: str,
        idempotency_key: str,
        project_id: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="project",
            action="edit",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=project_id,
            version=version,
        )

    async def aupdate_project(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.update_project, **kwargs)

    def add_comment_project(
        self, *, principal: Principal, data: CommentCreate, request_id: str, idempotency_key: str, project_id: str
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="project",
            action="comment",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=project_id,
        )

    async def aadd_comment_project(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.add_comment_project, **kwargs)

    def create_task(
        self, *, principal: Principal, data: TaskCreate, request_id: str, idempotency_key: str, product_id: str
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="task",
            action="create",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            product_id=product_id,
        )

    async def acreate_task(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.create_task, **kwargs)

    def update_task(
        self,
        *,
        principal: Principal,
        data: TaskPatch,
        request_id: str,
        idempotency_key: str,
        task_id: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="task",
            action="edit",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=task_id,
            version=version,
        )

    async def aupdate_task(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.update_task, **kwargs)

    def transition_task(
        self,
        *,
        principal: Principal,
        data: Transition,
        request_id: str,
        idempotency_key: str,
        task_id: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="task",
            action="transition",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=task_id,
            version=version,
        )

    async def atransition_task(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.transition_task, **kwargs)

    def add_comment_task(
        self, *, principal: Principal, data: CommentCreate, request_id: str, idempotency_key: str, task_id: str
    ) -> Dict[str, Any]:
        return self._mutate(
            principal=principal,
            kind="task",
            action="comment",
            data=data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            record_id=task_id,
        )

    async def aadd_comment_task(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.add_comment_task, **kwargs)

    def archive_task(self, *, task_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self._mutate(kind="task", action="archive", record_id=task_id, **kwargs)

    async def aarchive_task(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.archive_task, **kwargs)

    def restore_task(self, *, task_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self._mutate(kind="task", action="restore", record_id=task_id, **kwargs)

    async def arestore_task(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.restore_task, **kwargs)

    def archive_project(self, *, project_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self._mutate(kind="project", action="archive", record_id=project_id, **kwargs)

    async def aarchive_project(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.archive_project, **kwargs)

    def restore_project(self, *, project_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self._mutate(kind="project", action="restore", record_id=project_id, **kwargs)

    async def arestore_project(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.restore_project, **kwargs)

    def update_project_summary(self, *, project_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self._mutate(kind="project", action="summary", record_id=project_id, **kwargs)

    async def aupdate_project_summary(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.update_project_summary, **kwargs)

    def run_task(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return self._runtime.run_task(**kwargs)

    async def arun_task(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return await self._runtime.arun_task(**kwargs)

    def list_runs(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return self._runtime.list_runs(**kwargs)

    async def alist_runs(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return await self._runtime.alist_runs(**kwargs)

    def cancel_task_run(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return self._runtime.cancel_task_run(**kwargs)

    async def acancel_task_run(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return await self._runtime.acancel_task_run(**kwargs)

    def set_schedule(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return self._runtime.set_schedule(**kwargs)

    async def aset_schedule(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.set_schedule, **kwargs)

    def get_task_result(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return self._runtime.get_task_result(**kwargs)

    async def aget_task_result(self, **kwargs: Any) -> Dict[str, Any]:
        if self._runtime is None:
            raise CompanyError(503, "runtime_required", "Configure Company on AgentOS for execution")
        return await self._runtime.aget_task_result(**kwargs)

    def set_review_pull_request(self, *, task_id: str, data: PullRequestReview, **kwargs: Any) -> Dict[str, Any]:
        """Let an eligible human bind the current review to an exact GitHub PR revision."""
        return self._mutate(kind="task", action="pull_request", record_id=task_id, data=data, **kwargs)

    async def aset_review_pull_request(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.set_review_pull_request, **kwargs)
