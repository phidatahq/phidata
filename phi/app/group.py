from typing import List, Optional

from pydantic import BaseModel

from phi.infra.app.base import InfraApp


class AppGroup(BaseModel):
    """AppGroup is a collection of Apps"""

    name: Optional[str] = None
    enabled: bool = True
    apps: Optional[List[InfraApp]] = None

    class Config:
        arbitrary_types_allowed = True

    def get_apps(self) -> List[InfraApp]:
        if self.enabled and self.apps is not None:
            for app in self.apps:
                app.group = self.name
            return self.apps
        return []
