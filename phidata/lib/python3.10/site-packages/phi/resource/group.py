from typing import List, Optional

from pydantic import BaseModel

from phi.resource.base import ResourceBase


class ResourceGroup(BaseModel):
    """ResourceGroup is a collection of Resources"""

    name: Optional[str] = None
    enabled: bool = True
    resources: Optional[List[ResourceBase]] = None

    class Config:
        arbitrary_types_allowed = True

    def get_resources(self) -> List[ResourceBase]:
        if self.enabled and self.resources is not None:
            for resource in self.resources:
                if resource.group is None and self.name is not None:
                    resource.group = self.name
            return self.resources
        return []
