"""Product request and response schemas."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


ProjectStatus = Literal["proposed", "active", "done", "cancelled"]
TaskStatus = Literal["backlog", "ready", "in_progress", "in_review", "done", "cancelled"]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    outcome: Optional[str] = None
    target_date: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        if value is None or not value.strip():
            raise ValueError("name must be a non-empty string")
        return value


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    outcome: Optional[str] = None
    target_date: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        if value is None or not value.strip():
            raise ValueError("name must be a non-empty string")
        return value


class ProjectResponse(BaseModel):
    product_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    outcome: Optional[str] = None
    target_date: Optional[int] = None
    id: str
    status: ProjectStatus
    user_id: Optional[str] = None
    transitions: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: int
    updated_at: Optional[int] = None
    deleted_at: Optional[int] = None


class ProjectTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: ProjectStatus
    reason: str = Field(..., min_length=1)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A transition requires a non-empty reason")
        return value


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    brief: Optional[str] = None
    project_id: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        if value is None or not value.strip():
            raise ValueError("title must be a non-empty string")
        return value


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    brief: Optional[str] = None
    project_id: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        if value is None or not value.strip():
            raise ValueError("title must be a non-empty string")
        return value


class TaskResponse(BaseModel):
    product_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    brief: Optional[str] = None
    project_id: Optional[str] = None
    id: str
    status: TaskStatus
    user_id: Optional[str] = None
    transitions: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: int
    updated_at: Optional[int] = None
    deleted_at: Optional[int] = None
    executor_type: Optional[str] = None
    executor_id: Optional[str] = None
    accepted_by: Optional[str] = None
    accepted_at: Optional[int] = None


class TaskTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: TaskStatus
    reason: str = Field(..., min_length=1)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A transition requires a non-empty reason")
        return value

    executor_type: Optional[Literal["agent", "team", "workflow", "engineering"]] = None
    executor_id: Optional[str] = Field(None, min_length=1)

    @model_validator(mode="after")
    def validate_executor(self) -> "TaskTransition":
        if self.target == "ready":
            if self.executor_type is None or self.executor_id is None or not self.executor_id.strip():
                raise ValueError("Ready requires an executor type and id")
        elif self.executor_type is not None or self.executor_id is not None:
            raise ValueError("Only Ready can set an executor")
        return self
