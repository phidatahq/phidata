from typing import Optional, Union, List, Dict

from phi.docker.app.airflow.base import AirflowBase, ContainerContext


class AirflowWorker(AirflowBase):
    # -*- App Name
    name: str = "airflow-worker"

    # Command for the container
    command: Optional[Union[str, List[str]]] = "worker"

    # Queue name for the worker
    queue_name: str = "default"

    # Open the worker_log_port if open_worker_log_port=True
    # When you start an airflow worker, airflow starts a tiny web server subprocess to serve the workers
    # local log files to the airflow main web server, which then builds pages and sends them to users.
    # This defines the port on which the logs are served. It needs to be unused, and open visible from
    # the main web server to connect into the workers.
    open_worker_log_port: bool = True
    # Worker log port number on the container
    worker_log_port: int = 8793
    # Worker log port number on the container
    worker_log_host_port: Optional[int] = None

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        container_env: Dict[str, str] = super().get_container_env(container_context=container_context)

        # Set the queue name
        container_env["QUEUE_NAME"] = self.queue_name

        # Set the worker log port
        if self.open_worker_log_port:
            container_env["AIRFLOW__LOGGING__WORKER_LOG_SERVER_PORT"] = str(self.worker_log_port)

        return container_env

    def get_container_ports(self) -> Dict[str, int]:
        container_ports: Dict[str, int] = super().get_container_ports()

        # if open_worker_log_port = True, open the worker_log_port_number
        if self.open_worker_log_port and self.worker_log_host_port is not None:
            # Open the port
            container_ports[str(self.worker_log_port)] = self.worker_log_host_port

        return container_ports
