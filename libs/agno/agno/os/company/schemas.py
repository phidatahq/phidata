"""Company's versioned manual API contract."""

from datetime import date, datetime
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

Role = Literal["reader", "contributor", "owner"]
ProjectStatus = Literal["empty", "active", "completed"]
TaskStatus = Literal["backlog", "ready", "in_progress", "in_review", "done"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Evidence(Input):
    type: str = Field(default="link", min_length=1, max_length=80)
    url: HttpUrl
    label: Optional[str] = Field(default=None, max_length=200)


class PullRequestReview(Input):
    url: str = Field(pattern=r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[1-9][0-9]*$")
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class Repository(Input):
    url: str = Field(max_length=500, pattern=r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    branch: str = Field(default="main", min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_./-]+$")

    @model_validator(mode="after")
    def valid_path(self) -> "Repository":
        if any(part in (".", "..") for part in self.url.split("/")[-2:]):
            raise ValueError("Use a GitHub repository URL")
        return self


class CompanySetup(Input):
    repository: Optional[Repository] = None
    agent_id: Optional[str] = Field(default=None, min_length=1, max_length=200)


class ProductCreate(Input):
    repository: Optional[Repository] = None
    agent_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    instructions: str = Field(default="", max_length=10000)
    owner_id: Optional[str] = Field(default=None, min_length=1, max_length=200)


class Patch(Input):
    @model_validator(mode="after")
    def nonempty(self) -> "Patch":
        if not self.model_fields_set:
            raise ValueError("Supply at least one field")
        for field in self.model_fields_set:
            if getattr(self, field) is None and field not in (
                "target_date",
                "due_date",
                "assignee_id",
                "project_id",
                "agent_id",
                "repository",
            ):
                raise ValueError(f"{field} cannot be null")
        return self


class ProductPatch(Patch):
    repository: Optional[Repository] = None
    agent_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    instructions: Optional[str] = Field(default=None, max_length=10000)


class ProjectCreate(Input):
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(default="", max_length=10000)
    owner_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    target_date: Optional[date] = None


class ProjectPatch(Patch):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    instructions: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    owner_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    target_date: Optional[date] = None


class TaskCreate(Input):
    agent_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    project_id: Optional[UUID] = None
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(default="", max_length=10000)
    accountable_owner_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    assignee_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    due_date: Optional[date] = None
    evidence: List[Evidence] = Field(default_factory=list, max_length=20)


class TaskPatch(Patch):
    agent_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    project_id: Optional[UUID] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    instructions: Optional[str] = Field(default=None, max_length=10000)
    accountable_owner_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    assignee_id: Optional[str] = Field(default=None, min_length=1, max_length=200)
    priority: Optional[Literal["low", "normal", "high", "urgent"]] = None
    due_date: Optional[date] = None
    evidence: Optional[List[Evidence]] = Field(default=None, max_length=20)


class Transition(Input):
    to_status: str = Field(min_length=1, max_length=30)
    reason: str = Field(default="", max_length=10000)
    evidence: List[Evidence] = Field(default_factory=list, max_length=20)
    acceptance_check: str = Field(default="", max_length=10000)


class Reason(Input):
    reason: str = Field(min_length=1, max_length=10000)


class MemberCreate(Input):
    principal_id: str = Field(min_length=1, max_length=200)
    role: Role


class MemberPatch(Input):
    role: Role
    active: bool = True


class CommentCreate(Input):
    body: str = Field(min_length=1, max_length=10000)


class Counts(BaseModel):
    accepted_tasks: int
    done_tasks: int
    in_review: int
    total_tasks: int = 0
    backlog: int = 0
    ready: int = 0
    in_progress: int = 0
    active_projects: int = 0
    as_of: datetime


class Record(BaseModel):
    id: UUID
    key: str
    version: int
    created_at: datetime
    updated_at: datetime
    permitted_actions: List[str] = Field(default_factory=list)


class Product(Record):
    repository: Optional[Repository] = None
    builtin: Optional[Literal["agentos"]] = None
    name: str
    agent_id: Optional[str] = None
    instructions: str
    owner_id: str
    state: Literal["active", "archived"]
    counts: Counts
    latest_activity_at: Optional[datetime] = None


class Project(Record):
    product_id: UUID
    title: str
    instructions: str
    owner_id: str
    status: ProjectStatus
    state: Literal["active", "archived"]
    summary: str = ""
    summary_at: Optional[datetime] = None
    summary_sources: Dict[str, int] = Field(default_factory=dict)
    target_date: Optional[date] = None
    counts: Counts


class Task(Record):
    source: Optional[Dict[str, str]] = None
    product_id: UUID
    project_id: Optional[UUID] = None
    title: str
    instructions: str
    accountable_owner_id: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    state: Literal["active", "archived"]
    agent_id: Optional[str] = None
    priority: str
    due_date: Optional[date] = None
    origin: Literal["human", "agent"]
    schedule: Optional[Dict[str, Any]] = None
    schedule_id: Optional[str] = None
    review_pull_request: Optional[PullRequestReview] = None
    review_started_at: Optional[datetime] = None
    automation_error: Optional[str] = None
    accepted_by: Optional[str] = None
    accepted_at: Optional[datetime] = None
    evidence: List[Evidence]
    completed_at: Optional[datetime] = None


class Membership(BaseModel):
    product_id: UUID
    principal_id: str
    role: Role
    active: bool
    version: int


class Comment(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    author_id: str
    body: str
    created_at: datetime


class Activity(BaseModel):
    id: UUID
    product_id: UUID
    subject_type: str
    subject_id: UUID
    actor_id: str
    initiating_principal_id: str
    operation: str
    delta: Dict[str, Any]
    request_id: str
    created_at: datetime


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    data: List[T]
    next_cursor: Optional[str] = None


class Caller(BaseModel):
    principal_id: str
    company_access: bool
    permitted_actions: List[str]


class ListQuery(Input):
    key: Optional[str] = Field(default=None, min_length=1, max_length=80)
    limit: int = Field(default=50, ge=1, le=100)
    cursor: Optional[str] = Field(default=None, max_length=2000)
    product_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    status: Optional[str] = Field(default=None, max_length=30)
    state: Optional[Literal["active", "archived", "all"]] = None
    owner_id: Optional[str] = Field(default=None, max_length=200)
    assignee_id: Optional[str] = Field(default=None, max_length=200)
    direct: bool = False
    subject_type: Optional[Literal["product", "project", "task", "membership", "comment"]] = None
    subject_id: Optional[UUID] = None

    @model_validator(mode="after")
    def consistent(self) -> "ListQuery":
        if self.direct and self.project_id:
            raise ValueError("direct cannot be combined with project_id")
        return self


class RunTask(Input):
    message: str = Field(default="", max_length=10000)


class ProjectSummary(Input):
    summary: str = Field(min_length=1, max_length=10000)
    source_versions: Dict[str, int]


class TaskSchedule(Input):
    cron: str = Field(min_length=1, max_length=100)
    timezone: str = Field(default="UTC", min_length=1, max_length=100)
    enabled: bool = True

    @model_validator(mode="after")
    def valid_schedule(self) -> "TaskSchedule":
        from agno.scheduler.cron import validate_cron_expr, validate_timezone

        if not validate_cron_expr(self.cron) or len(self.cron.split()) != 5:
            raise ValueError("Use a valid five-field cron expression")
        if not validate_timezone(self.timezone):
            raise ValueError("Use a valid IANA time zone")
        return self


class FileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=1000)
    content: str = Field(max_length=1_000_000)
    expected_version: int = Field(ge=0)
