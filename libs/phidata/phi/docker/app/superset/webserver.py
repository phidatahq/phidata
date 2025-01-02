from typing import Optional, Union, List

from phi.docker.app.superset.base import SupersetBase


class SupersetWebserver(SupersetBase):
    # -*- App Name
    name: str = "superset-ws"

    # Command for the container
    command: Optional[Union[str, List[str]]] = "webserver"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8088
