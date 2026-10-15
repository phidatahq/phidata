"""Product and membership operations with service-level access checks."""

import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agno.db.base import AsyncBaseDb
from agno.db.schemas.company import CompanyConflict, CompanyForbidden, CompanyNotFound
from agno.os.company.schemas import ProductCreate, ProductUpdate, ProductVersion


class AsyncCompanyService:
    def __init__(self, db: AsyncBaseDb):
        self.db = db

    async def _member(self, user_id: str, product_id: str, owner: bool = False) -> Dict[str, Any]:
        if not user_id.strip():
            raise CompanyForbidden("Authenticated user required")
        member = await self.db.get_member(product_id, user_id)
        if member is None:
            raise CompanyNotFound("Product not found")
        if owner and member["role"] != "owner":
            raise CompanyForbidden("Product owner required")
        return member

    async def create_product(self, user_id: str, name: str, purpose: str = "") -> Dict[str, Any]:
        """Create a Product and its creator's owner membership atomically."""
        if not user_id.strip():
            raise CompanyForbidden("Authenticated user required")
        data = ProductCreate(name=name, purpose=purpose)
        now = int(time.time())
        return await self.db.create_product(
            dict(
                id=str(uuid4()),
                name=data.name,
                purpose=data.purpose,
                owner_id=user_id,
                status="active",
                version=1,
                created_at=now,
                updated_at=now,
            )
        )

    async def get_product(self, user_id: str, product_id: str) -> Dict[str, Any]:
        """Read a Product visible to this caller."""
        await self._member(user_id, product_id)
        product = await self.db.get_product(product_id)
        if product is None:
            raise CompanyNotFound("Product not found")
        return product

    async def list_products(
        self, user_id: str, status: Optional[str] = None, limit: int = 50, page: int = 1
    ) -> List[Dict[str, Any]]:
        """Apply membership in storage before paginating."""
        if not user_id.strip():
            raise CompanyForbidden("Authenticated user required")
        if status not in (None, "active", "archived") or not 1 <= limit <= 100 or page < 1:
            raise ValueError("Invalid status or pagination")
        return await self.db.list_products(user_id, status=status, limit=limit, page=page)

    async def update_product(
        self,
        user_id: str,
        product_id: str,
        expected_version: int,
        *,
        name: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Owners edit descriptive fields with compare-and-swap protection."""
        await self._member(user_id, product_id, owner=True)
        data = ProductUpdate(expected_version=expected_version, name=name, purpose=purpose)
        fields = data.model_dump(exclude_none=True, exclude={"expected_version"})
        product = await self.db.update_product(product_id, data.expected_version, actor_id=user_id, **fields)
        if product is None:
            raise CompanyConflict("Product version changed; reload before retrying")
        return product

    async def archive_product(self, user_id: str, product_id: str, expected_version: int) -> Dict[str, Any]:
        """Archive an owner-visible Product without deleting its records."""
        await self._member(user_id, product_id, owner=True)
        product = await self.db.update_product(
            product_id,
            ProductVersion(expected_version=expected_version).expected_version,
            actor_id=user_id,
            status="archived",
        )
        if product is None:
            raise CompanyConflict("Product version changed; reload before retrying")
        return product

    async def restore_product(self, user_id: str, product_id: str, expected_version: int) -> Dict[str, Any]:
        """Restore an archived Product."""
        await self._member(user_id, product_id, owner=True)
        product = await self.db.update_product(
            product_id,
            ProductVersion(expected_version=expected_version).expected_version,
            actor_id=user_id,
            status="active",
        )
        if product is None:
            raise CompanyConflict("Product version changed; reload before retrying")
        return product

    async def add_member(self, user_id: str, product_id: str, member_id: str, role: str = "member") -> Dict[str, Any]:
        """An owner adds a member or changes their role."""
        await self._member(user_id, product_id, owner=True)
        return await self.db.upsert_member(product_id, member_id, role, actor_id=user_id)

    async def remove_member(self, user_id: str, product_id: str, member_id: str) -> bool:
        """Remove a member, preserving the last owner under concurrency."""
        await self._member(user_id, product_id, owner=True)
        return await self.db.delete_member(product_id, member_id, actor_id=user_id)

    async def list_members(self, user_id: str, product_id: str) -> List[Dict[str, Any]]:
        """Read memberships in a visible Product."""
        await self._member(user_id, product_id)
        return await self.db.list_members(product_id)
