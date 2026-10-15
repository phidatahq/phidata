from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ProductPurpose = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProductName
    purpose: ProductPurpose


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1, strict=True)
    name: Optional[ProductName] = None
    purpose: Optional[ProductPurpose] = None

    @model_validator(mode="after")
    def validate_changes(self) -> "ProductUpdate":
        changes = self.model_fields_set - {"expected_version"}
        if not changes or any(getattr(self, field) is None for field in changes):
            raise ValueError("Provide a non-null name or purpose to update")
        return self


class Product(BaseModel):
    id: str
    name: str
    purpose: str
    owner_id: str
    version: int
    created_at: datetime
    updated_at: datetime
