from typing import Optional, Union, List

from phi.k8s.app.airflow.base import AirflowBase


class AirflowWebserver(AirflowBase):
    # -*- App Name
    name: str = "airflow-ws"

    # Command for the container
    command: Optional[Union[str, List[str]]] = "webserver"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8080

    # -*- Service Configuration
    create_service: bool = True
