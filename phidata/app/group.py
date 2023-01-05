from typing import List, Optional

from pydantic import BaseModel

from phidata.app.phidata_app import PhidataApp


class AppGroup(BaseModel):
    """
    The AppGroup is a collection of PhidataApps acting as a single unit.
    """

    # Name
    name: Optional[str] = None
    enabled: bool = True
    # Apps
    apps: Optional[List[PhidataApp]] = None

    class Config:
        arbitrary_types_allowed = True

    def get_apps(self) -> List[PhidataApp]:
        if self.enabled and self.apps is not None:
            return self.apps
        return []


def get_apps_from_app_groups(app_groups: List[AppGroup]) -> List[PhidataApp]:
    apps = []
    for app_group in app_groups:
        apps.extend(app_group.get_apps())
    return apps
