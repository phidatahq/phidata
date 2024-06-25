from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from phi.app.base import AppBase


class AppGroup(BaseModel):
    """AppGroup is a collection of Apps"""

    name: Optional[str] = None
    enabled: bool = True
    apps: Optional[List[AppBase]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_apps(self) -> List[AppBase]:
        if self.enabled and self.apps is not None:
            for app in self.apps:
                if app.group is None and self.name is not None:
                    app.group = self.name
            return self.apps
        return []
