"""Company HTTP models. Identity and timestamps are server-owned."""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CompanyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProductCreate(CompanyRequest):
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(default="", max_length=20000)


class ProductVersion(CompanyRequest):
    expected_version: int = Field(ge=1, strict=True)


class ProductUpdate(ProductVersion):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    purpose: Optional[str] = Field(default=None, max_length=20000)


class MemberPut(CompanyRequest):
    role: Literal["owner", "member"]


class ProductResponse(BaseModel):
    id: str
    name: str
    purpose: str
    owner_id: str
    status: Literal["active", "archived"]
    version: int
    created_at: int
    updated_at: int


class MemberResponse(BaseModel):
    product_id: str
    user_id: str
    role: Literal["owner", "member"]
    created_at: int
    updated_at: int


class ProductList(BaseModel):
    data: List[ProductResponse]


class MemberList(BaseModel):
    data: List[MemberResponse]
