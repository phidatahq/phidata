from uuid import UUID
from typing import Optional, Dict, Any

from pydantic import BaseModel


class PromptRegistrySync(BaseModel):
    """Data sent to API to sync a prompt registry"""

    registry_name: str
    registry_data: Optional[Dict[str, Any]] = None


class PromptTemplateSync(BaseModel):
    """Data sent to API to sync a single prompt template"""

    template_id: str
    template_data: Optional[Dict[str, Any]] = None


class PromptTemplatesSync(BaseModel):
    """Data sent to API to sync prompt templates"""

    templates: Dict[str, PromptTemplateSync] = {}


class PromptRegistrySchema(BaseModel):
    """Schema for a prompt registry returned by API"""

    id_user: Optional[int] = None
    id_workspace: Optional[int] = None
    id_registry: Optional[UUID] = None
    registry_name: Optional[str] = None
    registry_data: Optional[Dict[str, Any]] = None


class PromptTemplateSchema(BaseModel):
    """Schema for a prompt template returned by API"""

    id_template: Optional[UUID] = None
    id_registry: Optional[UUID] = None
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
