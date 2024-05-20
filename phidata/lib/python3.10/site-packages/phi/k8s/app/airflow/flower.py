from typing import Optional, Union, List

from phi.k8s.app.airflow.base import AirflowBase


class AirflowFlower(AirflowBase):
    # -*- App Name
    name: str = "airflow-flower"

    # Command for the container
    command: Optional[Union[str, List[str]]] = "flower"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 5555

    # -*- Service Configuration
    create_service: bool = True
