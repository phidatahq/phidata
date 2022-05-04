import base64
from typing import Optional, Dict, List
from kubernetes.client import CoreV1Api
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.stream import stream
from kubernetes.stream.ws_client import WSClient

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.core.v1.pod import Pod
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger


def execute_command(
    cmd: List[str],
    pod: Pod,
    k8s_api_client: K8sApiClient,
    container_name: Optional[str] = None,
    wait: bool = True,
    print_output: bool = True,
    k8s_env: Optional[Dict[str, str]] = None,
) -> bool:
    import os
    import socket
    import time

    active_pod: Optional[V1Pod] = pod.read(k8s_api_client)
    # logger.debug("active_pod: {}".format(active_pod.metadata))
    if active_pod is None or not isinstance(active_pod, V1Pod):
        print_error("V1Pod not found")
        return False

    pod_name = active_pod.metadata.name
    print_info(
        "\nRunning command: {}\nPod: {}\nContainer: {}\n".format(
            cmd, pod_name, container_name
        )
    )
    core_v1_api: CoreV1Api = k8s_api_client.core_v1_api

    ws_connection: WSClient = stream(
        core_v1_api.connect_get_namespaced_pod_exec,
        pod_name,
        pod.get_namespace(),
        command=cmd,
        container=container_name,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
        _preload_content=False,
    )
    # print_info(ws_connection)

    # ws_connection.is_open() returns True if the connection is alive
    while ws_connection.is_open():
        ws_connection.update(timeout=5)
        if ws_connection.peek_stdout():
            op_line: str = ws_connection.read_all()
            print_info(op_line)
    ws_connection.close()

    return True
