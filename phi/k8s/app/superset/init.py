from typing import Optional, Union, List

from phi.k8s.app.superset.base import SupersetBase, RestartPolicy


class SupersetInit(SupersetBase):
    # -*- App Name
    name: str = "superset-init"

    # Command for the container
    entrypoint: Optional[Union[str, List]] = "/scripts/init-superset.sh"

    # -*- Deployment Configuration
    restart_policy: Optional[RestartPolicy] = RestartPolicy.ON_FAILURE
