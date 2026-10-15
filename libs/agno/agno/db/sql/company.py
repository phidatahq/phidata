"""Company queries shared by the PostgreSQL and SQLite database adapters.

Adapters resolve tables and own transactions. A Product row write serializes all
mutations, including owner changes, across processes on both databases.
"""

import time
from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select

from agno.db.schemas.company import CompanyConflict, CompanyForbidden, CompanyNotFound


def get_product(conn: Any, products: Any, product_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(select(products).where(products.c.id == product_id)).mappings().first()
    return dict(row) if row is not None else None


def get_member(conn: Any, members: Any, product_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    row = (
        conn.execute(select(members).where(members.c.product_id == product_id, members.c.user_id == user_id))
        .mappings()
        .first()
    )
    return dict(row) if row is not None else None


def list_members(conn: Any, members: Any, product_id: str) -> List[Dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            select(members).where(members.c.product_id == product_id).order_by(members.c.user_id)
        ).mappings()
    ]


def create_product(conn: Any, products: Any, members: Any, product: Dict[str, Any]) -> Dict[str, Any]:
    conn.execute(insert(products).values(**product))
    conn.execute(
        insert(members).values(
            product_id=product["id"],
            user_id=product["owner_id"],
            role="owner",
            created_at=product["created_at"],
            updated_at=product["updated_at"],
        )
    )
    return dict(product)


def list_products(
    conn: Any,
    products: Any,
    members: Any,
    user_id: str,
    status: Optional[str],
    limit: Optional[int],
    page: Optional[int],
) -> List[Dict[str, Any]]:
    if limit is not None and limit < 1 or page is not None and page < 1:
        raise ValueError("limit and page must be positive")
    stmt = select(products).join(members, products.c.id == members.c.product_id).where(members.c.user_id == user_id)
    if status is not None:
        stmt = stmt.where(products.c.status == status)
    stmt = stmt.order_by(products.c.created_at, products.c.id)
    if limit is not None:
        stmt = stmt.limit(limit).offset(((page or 1) - 1) * limit)
    return [dict(row) for row in conn.execute(stmt).mappings()]


def _lock_product(conn: Any, products: Any, members: Any, product_id: str, actor_id: Optional[str]) -> Dict[str, Any]:
    # A no-op UPDATE obtains a row lock on PostgreSQL and a write lock on
    # SQLite before reading membership. It avoids a read-to-write upgrade race.
    row = (
        conn.execute(
            products.update().where(products.c.id == product_id).values(version=products.c.version).returning(products)
        )
        .mappings()
        .first()
    )
    if row is None:
        raise CompanyNotFound("Product not found")
    if actor_id is not None:
        member = get_member(conn, members, product_id, actor_id)
        if member is None:
            raise CompanyNotFound("Product not found")
        if member["role"] != "owner":
            raise CompanyForbidden("Product owner required")
    return dict(row)


def update_product(
    conn: Any,
    products: Any,
    members: Any,
    product_id: str,
    expected_version: int,
    actor_id: Optional[str],
    fields: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if set(fields) - {"name", "purpose", "status"}:
        raise ValueError("Unsupported Product fields")
    _lock_product(conn, products, members, product_id, actor_id)
    row = (
        conn.execute(
            products.update()
            .where(products.c.id == product_id, products.c.version == expected_version)
            .values(**fields, version=products.c.version + 1, updated_at=int(time.time()))
            .returning(products)
        )
        .mappings()
        .first()
    )
    return dict(row) if row is not None else None


def _remaining_owner(conn: Any, members: Any, product_id: str, user_id: str) -> str:
    owner = conn.execute(
        select(members.c.user_id)
        .where(members.c.product_id == product_id, members.c.role == "owner", members.c.user_id != user_id)
        .order_by(members.c.created_at, members.c.user_id)
    ).scalar()
    if owner is None:
        raise CompanyConflict("Cannot remove or demote the last owner")
    return str(owner)


def upsert_member(
    conn: Any, products: Any, members: Any, product_id: str, user_id: str, role: str, actor_id: Optional[str]
) -> Dict[str, Any]:
    if role not in ("owner", "member") or not user_id.strip():
        raise ValueError("A user and an owner or member role are required")
    product = _lock_product(conn, products, members, product_id, actor_id)
    existing = get_member(conn, members, product_id, user_id)
    now = int(time.time())
    if existing is not None:
        if existing["role"] == "owner" and role != "owner":
            replacement = _remaining_owner(conn, members, product_id, user_id)
            if product["owner_id"] == user_id:
                conn.execute(
                    products.update()
                    .where(products.c.id == product_id)
                    .values(owner_id=replacement, version=products.c.version + 1, updated_at=now)
                )
        conn.execute(
            members.update()
            .where(members.c.product_id == product_id, members.c.user_id == user_id)
            .values(role=role, updated_at=now)
        )
    else:
        conn.execute(
            insert(members).values(product_id=product_id, user_id=user_id, role=role, created_at=now, updated_at=now)
        )
    return {
        "product_id": product_id,
        "user_id": user_id,
        "role": role,
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }


def delete_member(
    conn: Any, products: Any, members: Any, product_id: str, user_id: str, actor_id: Optional[str]
) -> bool:
    product = _lock_product(conn, products, members, product_id, actor_id)
    existing = get_member(conn, members, product_id, user_id)
    if existing is None:
        return False
    if existing["role"] == "owner":
        replacement = _remaining_owner(conn, members, product_id, user_id)
        if product["owner_id"] == user_id:
            conn.execute(
                products.update()
                .where(products.c.id == product_id)
                .values(owner_id=replacement, version=products.c.version + 1, updated_at=int(time.time()))
            )
    conn.execute(members.delete().where(members.c.product_id == product_id, members.c.user_id == user_id))
    return True
