"""Explicit Product operations with service-level authorization and ownership."""

import asyncio
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import List, Optional, Union
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.engine import Connection

from agno.db.base import AsyncBaseDb, BaseDb
from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb
from agno.os.authz._request_scope import invalidate as invalidate_authorization_cache
from agno.os.company.schemas import Product, ProductCreate, ProductUpdate
from agno.os.company.storage import ProductStorage
from agno.os.middleware.jwt import is_reserved_principal
from agno.run.authorization import current_authorization

# Set only by the HTTP router on an OS with no authentication configured.
_local_access: ContextVar[bool] = ContextVar("company_local_access", default=False)


class CompanyAuthenticationError(PermissionError):
    """An authenticated human caller is required."""


class ProductNotFoundError(LookupError):
    """The Product does not exist or is not owned by the caller."""


class ProductConflictError(ValueError):
    """The Product changed since the caller read it."""


class CompanyService:
    """Owner-only Products, using the current trusted AgentOS authorization scope.

    Creation assigns the human caller as immutable owner. Platform permissions
    are necessary but never bypass ownership, including for administrators.
    On an unauthenticated OS, HTTP requests share the local development owner.
    Python callers must establish the existing ``authorization_scope`` in trusted
    application code. Never construct that scope from user or model arguments.
    """

    def __init__(self, db: Optional[Union[BaseDb, AsyncBaseDb]]):
        if db is None:
            raise ValueError("Company requires a database: pass AgentOS(db=...) or CompanyConfig(db=...).")
        if not (
            isinstance(db, PostgresDb)
            and db.db_engine.dialect.name == "postgresql"
            or isinstance(db, SqliteDb)
            and db.db_engine.dialect.name == "sqlite"
        ):
            raise ValueError("Company supports synchronous PostgreSQL via PostgresDb and SQLite via SqliteDb.")
        assert isinstance(db, (PostgresDb, SqliteDb))
        if isinstance(db, SqliteDb) and (
            db.db_engine.url.database in (None, "", ":memory:", "file::memory:")
            or db.db_engine.url.query.get("mode") == "memory"
        ):
            raise ValueError("Company requires file-backed SQLite so worker threads share persistent storage.")
        self.db = db
        self._storage = ProductStorage(db)

    def initialize_schema(self) -> None:
        """Explicit deployment operation; not exposed over HTTP or run at startup."""
        self._storage._initialize()

    async def ainitialize_schema(self) -> None:
        await asyncio.to_thread(self.initialize_schema)

    def _caller(self, action: str) -> str:
        authority = current_authorization()
        if authority is None and _local_access.get():
            return "local"
        principal = authority.context.principal_id if authority is not None else None
        if (
            authority is None
            or authority.service_account
            or not isinstance(principal, str)
            or not principal.strip()
            or is_reserved_principal(principal)
        ):
            raise CompanyAuthenticationError("Company requires an authenticated human caller.")
        # A lock wait can outlive a role revocation in another request. Discard
        # AgentOS request-local policy reads before asking the provider again.
        invalidate_authorization_cache()
        # Always enforce, including request scopes with enforce_tools=False.
        authority.require("company", action)
        return principal

    def create_product(self, product: ProductCreate) -> Product:
        owner = self._caller("write")
        now = datetime.now(timezone.utc)
        result = Product(
            id=str(uuid4()),
            name=product.name,
            purpose=product.purpose,
            owner_id=owner,
            version=1,
            created_at=now,
            updated_at=now,
        )
        with self._storage._write() as connection:
            self._storage._check_version(connection)
            self._caller("write")
            connection.execute(self._storage.products.insert().values(**result.model_dump()))
        return result

    async def acreate_product(self, product: ProductCreate) -> Product:
        return await asyncio.to_thread(self.create_product, product)

    def list_products(self, *, limit: int = 50, offset: int = 0) -> List[Product]:
        owner = self._caller("read")
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be 1..100 and offset must be non-negative")
        table = self._storage.products
        with self._storage.engine.connect() as connection:
            self._storage._check_version(connection)
            rows = connection.execute(
                select(table).where(table.c.owner_id == owner).order_by(table.c.id).limit(limit).offset(offset)
            ).mappings()
            return [Product.model_validate(dict(row)) for row in rows]

    async def alist_products(self, *, limit: int = 50, offset: int = 0) -> List[Product]:
        return await asyncio.to_thread(self.list_products, limit=limit, offset=offset)

    def get_product(self, product_id: str) -> Product:
        owner = self._caller("read")
        with self._storage.engine.connect() as connection:
            self._storage._check_version(connection)
            return self._owned(connection, product_id, owner)

    async def aget_product(self, product_id: str) -> Product:
        return await asyncio.to_thread(self.get_product, product_id)

    def _owned(self, connection: Connection, product_id: str, owner: str, *, lock: bool = False) -> Product:
        table = self._storage.products
        query = select(table).where(table.c.id == product_id, table.c.owner_id == owner)
        if lock:
            query = query.with_for_update()
        row = connection.execute(query).mappings().first()
        if row is None:
            raise ProductNotFoundError("Product not found.")
        return Product.model_validate(dict(row))

    def update_product(self, product_id: str, changes: ProductUpdate) -> Product:
        owner = self._caller("write")
        table = self._storage.products
        with self._storage._write() as connection:
            self._storage._check_version(connection)
            product = self._owned(connection, product_id, owner, lock=True)
            # A request may have waited on a concurrent writer. Recheck live policy
            # after acquiring the lock, before testing the revision or writing.
            self._caller("write")
            if product.version != changes.expected_version:
                raise ProductConflictError("Product version conflict; read the current Product and retry.")
            values = changes.model_dump(exclude_unset=True, exclude={"expected_version"})
            values.update(version=product.version + 1, updated_at=datetime.now(timezone.utc))
            row = (
                connection.execute(table.update().where(table.c.id == product_id).values(**values).returning(table))
                .mappings()
                .one()
            )
            return Product.model_validate(dict(row))

    async def aupdate_product(self, product_id: str, changes: ProductUpdate) -> Product:
        return await asyncio.to_thread(self.update_product, product_id, changes)

    def delete_product(self, product_id: str, *, expected_version: int) -> None:
        """Permanently remove an owned Product at exactly the supplied version."""
        owner = self._caller("delete")
        if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 1:
            raise ValueError("expected_version must be a positive integer")
        with self._storage._write() as connection:
            self._storage._check_version(connection)
            product = self._owned(connection, product_id, owner, lock=True)
            self._caller("delete")
            if product.version != expected_version:
                raise ProductConflictError("Product version conflict; read the current Product and retry.")
            connection.execute(self._storage.products.delete().where(self._storage.products.c.id == product_id))

    async def adelete_product(self, product_id: str, *, expected_version: int) -> None:
        await asyncio.to_thread(self.delete_product, product_id, expected_version=expected_version)
