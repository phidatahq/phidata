from typing import Optional, Union, List

from phi.k8s.app.superset.base import SupersetBase


class SupersetWorker(SupersetBase):
    # -*- App Name
    name: str = "superset-worker"

    # Command for the container
    command: Optional[Union[str, List[str]]] = "worker"
