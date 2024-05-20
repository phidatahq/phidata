from typing import Optional, Union, List, Dict

from phi.k8s.app.airflow.base import AirflowBase, ContainerContext


class AirflowWorker(AirflowBase):
    # -*- App Name
    name: str = "airflow-worker"

    # Command for the container
    command: Optional[Union[str, List[str]]] = "worker"

    # Queue name for the worker
    queue_name: str = "default"

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        container_env: Dict[str, str] = super().get_container_env(container_context=container_context)

        # Set the queue name
        container_env["QUEUE_NAME"] = self.queue_name

        return container_env
