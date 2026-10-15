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
