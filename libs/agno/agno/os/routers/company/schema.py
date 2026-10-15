"""Product request and response schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    purpose: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must be a non-empty string")
        return value


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        if value is None or not value.strip():
            raise ValueError("name must be a non-empty string")
        return value


class ProductResponse(BaseModel):
    id: str
    name: str
    purpose: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: int
    updated_at: Optional[int] = None
    deleted_at: Optional[int] = None
