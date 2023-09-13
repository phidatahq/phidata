from typing import Optional, Union, List

from phi.k8s.app.superset.base import SupersetBase


class SupersetWorkerBeat(SupersetBase):
    # -*- App Name
    name: str = "superset-worker-beat"

    # Command for the container
    command: Optional[Union[str, List[str]]] = "beat"
