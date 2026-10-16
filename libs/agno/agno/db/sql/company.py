"""Company archive transactions shared by the SQL adapters.

The adapters resolve tables and own the transaction. Async adapters use
AsyncSession.run_sync, so these same statements execute through their async driver.
Archive provenance lives in the existing JSON transition history, leaving lifecycle
status intact. Only the last archive event may authorize a cascading restore.
"""

import time
from typing import Any, Dict, List, Optional

from sqlalchemy import func, literal, or_, select, union_all


def active_parents(stmt: Any, table: Any, products: Any, projects: Any = None) -> Any:
    """Hide children of archived parents before counting or paging."""
    stmt = stmt.where(
        select(products.c.id).where(products.c.id == table.c.product_id, products.c.deleted_at.is_(None)).exists()
    )
    if projects is not None:
        stmt = stmt.where(
            or_(
                table.c.project_id.is_(None),
                select(projects.c.id)
                .where(projects.c.id == table.c.project_id, projects.c.deleted_at.is_(None))
                .exists(),
            )
        )
    return stmt


def lock_product(sess: Any, products: Any, product_id: str) -> None:
    """Serialize hierarchy writes on the Product, including on SQLite.

    A no-op UPDATE obtains a write lock without changing the activity timestamp.
    Every child creation, move, transition and restore shares this lock with archive.
    """
    stmt = products.update().where(products.c.id == product_id, products.c.deleted_at.is_(None))
    row = sess.execute(stmt.values(updated_at=products.c.updated_at).returning(products.c.id)).first()
    if row is None:
        raise ValueError("Product is missing or archived")


def require_project(sess: Any, projects: Any, project_id: Optional[str], product_id: str) -> None:
    if project_id is None:
        return
    row = sess.execute(select(projects).where(projects.c.id == project_id)).first()
    if row is None or row._mapping["deleted_at"] is not None:
        raise ValueError("Project is missing or archived")
    if row._mapping["product_id"] != product_id:
        raise ValueError("Task and Project must belong to the same Product")


def lock_child(sess: Any, products: Any, projects: Any, table: Any, record_id: str) -> None:
    row = sess.execute(select(table).where(table.c.id == record_id)).first()
    if row is None:
        return
    record = row._mapping
    lock_product(sess, products, record["product_id"])
    # Read the Project again after taking the Product lock: a move may have won it.
    if "project_id" in table.c:
        row = sess.execute(select(table).where(table.c.id == record_id)).one()
        require_project(sess, projects, row._mapping["project_id"], record["product_id"])


def _event(record: Dict[str, Any], action: str, now: int, parent: Optional[Dict[str, str]] = None) -> Any:
    return [
        *(record.get("transitions") or []),
        {
            "action": action,
            "from": record["status"],
            "target": record["status"],
            "reason": "Parent archived" if parent else ("Archived" if action == "archive" else "Restored"),
            "created_at": now,
            "user_id": None,
            "archived_by": parent,
        },
    ]


def task_restore_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    """Close a cascade event without changing standalone Task acceptance history.

    Ordinary Task archive only changes deleted_at. Its restore must also leave
    lifecycle history intact because queued execution fences against that history.
    """
    now = int(time.time())
    fields: Dict[str, Any] = {"deleted_at": None, "updated_at": now}
    history = record.get("transitions") or []
    if history and history[-1].get("action") == "archive":
        fields["transitions"] = _event(record, "restore", now)
    return fields


def _archive_children(sess: Any, table: Any, condition: Any, parent: Dict[str, str], now: int) -> None:
    rows = sess.execute(select(table).where(condition, table.c.deleted_at.is_(None))).mappings().all()
    for row in rows:
        sess.execute(
            table.update()
            .where(table.c.id == row["id"])
            .values(deleted_at=now, updated_at=now, transitions=_event(dict(row), "archive", now, parent))
        )


def _restore_children(sess: Any, table: Any, condition: Any, parent: Dict[str, str], now: int) -> None:
    rows = sess.execute(select(table).where(condition, table.c.deleted_at.is_not(None))).mappings().all()
    for row in rows:
        history = row["transitions"] or []
        if not history or history[-1].get("action") != "archive" or history[-1].get("archived_by") != parent:
            continue
        sess.execute(
            table.update()
            .where(table.c.id == row["id"])
            .values(deleted_at=None, updated_at=now, transitions=_event(dict(row), "restore", now))
        )


def _refuse_open_tasks(sess: Any, tasks: Any, condition: Any) -> None:
    rows = (
        sess.execute(
            select(tasks.c.id, tasks.c.title)
            .where(condition, tasks.c.status.in_(["ready", "in_progress", "in_review"]))
            .order_by(tasks.c.id)
        )
        .mappings()
        .all()
    )
    if rows:
        raise ValueError({"message": "Cannot archive with active Tasks", "tasks": [dict(row) for row in rows]})


def archive_product(
    sess: Any, products: Any, projects: Any, tasks: Any, product_id: str, user_id: Optional[str]
) -> bool:
    stmt = products.update().where(products.c.id == product_id, products.c.deleted_at.is_(None))
    if user_id is not None:
        stmt = stmt.where(products.c.user_id == user_id)
    now = int(time.time())
    # Lock and change the parent first; a refusal rolls back the whole transaction.
    if sess.execute(stmt.values(deleted_at=now, updated_at=now).returning(products.c.id)).first() is None:
        return False
    _refuse_open_tasks(sess, tasks, tasks.c.product_id == product_id)
    parent = {"type": "product", "id": product_id}
    _archive_children(sess, projects, projects.c.product_id == product_id, parent, now)
    _archive_children(sess, tasks, tasks.c.product_id == product_id, parent, now)
    return True


def restore_product(
    sess: Any, products: Any, projects: Any, tasks: Any, product_id: str, user_id: Optional[str]
) -> Optional[Dict[str, Any]]:
    stmt = products.update().where(products.c.id == product_id, products.c.deleted_at.is_not(None))
    if user_id is not None:
        stmt = stmt.where(products.c.user_id == user_id)
    now = int(time.time())
    row = sess.execute(stmt.values(deleted_at=None, updated_at=now).returning(products)).first()
    if row is None:
        return None
    parent = {"type": "product", "id": product_id}
    _restore_children(sess, projects, projects.c.product_id == product_id, parent, now)
    _restore_children(sess, tasks, tasks.c.product_id == product_id, parent, now)
    return dict(row._mapping)


def archive_project(
    sess: Any, products: Any, projects: Any, tasks: Any, project_id: str, user_id: Optional[str]
) -> bool:
    lock_child(sess, products, projects, projects, project_id)
    stmt = select(projects).where(projects.c.id == project_id, projects.c.deleted_at.is_(None))
    if user_id is not None:
        stmt = stmt.where(projects.c.user_id == user_id)
    row = sess.execute(stmt).first()
    if row is None:
        return False
    _refuse_open_tasks(sess, tasks, tasks.c.project_id == project_id)
    now = int(time.time())
    sess.execute(
        projects.update()
        .where(projects.c.id == project_id)
        .values(deleted_at=now, updated_at=now, transitions=_event(dict(row._mapping), "archive", now))
    )
    _archive_children(sess, tasks, tasks.c.project_id == project_id, {"type": "project", "id": project_id}, now)
    return True


def restore_project(
    sess: Any, products: Any, projects: Any, tasks: Any, project_id: str, user_id: Optional[str]
) -> Optional[Dict[str, Any]]:
    lock_child(sess, products, projects, projects, project_id)
    stmt = select(projects).where(projects.c.id == project_id, projects.c.deleted_at.is_not(None))
    if user_id is not None:
        stmt = stmt.where(projects.c.user_id == user_id)
    row = sess.execute(stmt).first()
    if row is None:
        return None
    now = int(time.time())
    restored = sess.execute(
        projects.update()
        .where(projects.c.id == project_id)
        .values(deleted_at=None, updated_at=now, transitions=_event(dict(row._mapping), "restore", now))
        .returning(projects)
    ).one()
    _restore_children(sess, tasks, tasks.c.project_id == project_id, {"type": "project", "id": project_id}, now)
    return dict(restored._mapping)


def product_counts(
    sess: Any, products: Any, projects: Any, tasks: Any, product_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    """One grouped SQL statement for both kinds of child on a Product page."""
    from agno.db.schemas.tasks import TASK_TRANSITIONS

    counts: Dict[str, Dict[str, Any]] = {
        pid: {"projects": 0, "tasks": dict.fromkeys(TASK_TRANSITIONS, 0)} for pid in product_ids
    }
    if not product_ids:
        return counts
    project_query = active_parents(
        select(projects.c.product_id.label("parent_id"), literal("projects").label("kind"), func.count().label("total"))
        .where(
            projects.c.product_id.in_(product_ids),
            projects.c.deleted_at.is_(None),
            projects.c.status.in_(["proposed", "active"]),
        )
        .group_by(projects.c.product_id),
        projects,
        products,
    )
    task_query = active_parents(
        select(tasks.c.product_id.label("parent_id"), tasks.c.status.label("kind"), func.count().label("total"))
        .where(tasks.c.product_id.in_(product_ids), tasks.c.deleted_at.is_(None))
        .group_by(tasks.c.product_id, tasks.c.status),
        tasks,
        products,
        projects,
    )
    for row in sess.execute(union_all(project_query, task_query)).mappings():
        if row["kind"] == "projects":
            counts[row["parent_id"]]["projects"] = row["total"]
        else:
            counts[row["parent_id"]]["tasks"][row["kind"]] = row["total"]
    return counts


def project_counts(
    sess: Any, products: Any, projects: Any, tasks: Any, project_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    """One grouped SQL statement for all Task statuses on a Project page."""
    from agno.db.schemas.tasks import TASK_TRANSITIONS

    counts: Dict[str, Dict[str, Any]] = {pid: {"tasks": dict.fromkeys(TASK_TRANSITIONS, 0)} for pid in project_ids}
    if not project_ids:
        return counts
    query = active_parents(
        select(tasks.c.project_id, tasks.c.status, func.count().label("total"))
        .where(tasks.c.project_id.in_(project_ids), tasks.c.deleted_at.is_(None))
        .group_by(tasks.c.project_id, tasks.c.status),
        tasks,
        products,
        projects,
    )
    for row in sess.execute(query).mappings():
        counts[row["project_id"]]["tasks"][row["status"]] = row["total"]
    return counts
