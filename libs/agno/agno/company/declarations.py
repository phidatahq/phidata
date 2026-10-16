"""Validated declarations shared by code, YAML and blank-deployment setup."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agno.db.schemas.sources import validate_source_fields


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = None
    type: Literal["git", "markdown", "website"]
    reference: str
    credential_ref: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_reader(self):
        validate_source_fields(self.model_dump(exclude={"id"}))
        return self


class Routine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    template: Literal["refresh", "intake", "summary"]
    executor_type: Literal["agent", "team", "workflow"]
    executor_id: str = Field(min_length=1)
    cron_expr: str
    timezone: str = "UTC"
    instructions: Optional[str] = None
    auto_accept: Literal[False] = False

    @model_validator(mode="after")
    def validate_schedule(self):
        from agno.scheduler.cron import validate_cron_expr, validate_timezone

        if not validate_cron_expr(self.cron_expr):
            raise ValueError("Invalid cron expression")
        if not validate_timezone(self.timezone):
            raise ValueError("Invalid timezone")
        return self


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = None
    name: str = Field(min_length=1)
    purpose: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sources: List[Source] = Field(default_factory=list)
    routines: List[Routine] = Field(default_factory=list)


class CompanyDeclarations(BaseModel):
    """Validated YAML declarations; runtime dependencies are supplied in code."""

    model_config = ConfigDict(extra="forbid")
    products: List[Product] = Field(default_factory=list)


class IntakeProposal(BaseModel):
    """An actionable proposal selected by the reader, not one Task per file."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1)
    brief: str = Field(min_length=1)
    proposal_key: str = Field(min_length=1)
    evidence_links: List[str] = Field(min_length=1)
    evidence_hashes: Dict[str, str] = Field(min_length=1, description="Observed content hash for each selected link")
