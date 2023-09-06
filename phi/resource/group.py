from typing import List, Optional

from pydantic import BaseModel

from phi.infra.resource.base import InfraResource


class ResourceGroup(BaseModel):
    """ResourceGroup is a collection of Resources"""

    name: Optional[str] = None
    enabled: bool = True
    resources: Optional[List[InfraResource]] = None

    class Config:
        arbitrary_types_allowed = True

    def get_resources(self) -> List[InfraResource]:
        if self.enabled and self.resources is not None:
            for resource in self.resources:
                resource.group = self.name
            return self.resources
        return []
