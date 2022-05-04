from typing import Optional, Dict

from docker.models.containers import Container
from docker.errors import APIError

from phidata.utils.log import logger


def execute_command(
    cmd: str,
    container: Container,
    wait: bool = True,
    detach: bool = False,
    print_output: bool = True,
    docker_env: Optional[Dict[str, str]] = None,
) -> bool:
    """

    :param cmd:
    :param container:
    :param wait:
    :param detach:
    :param print_output:
    :param docker_env:
    :return:

    TODO:
    * Run a detached command
    * Return False on failure, currently only True is returned
    """
    import os
    import socket
    import time

    try:
        logger.debug("Exec `{}` in container: {}".format(cmd, container.name))
        _container_socket: Optional[socket.SocketIO] = None
        exit_code, _container_socket = container.exec_run(
            cmd=cmd,
            stdout=True,
            stdin=True,
            tty=True,
            socket=True,
            environment=docker_env,
        )
        # logger.debug(f"exit_code: {exit_code}")
        # logger.debug(f"_container_socket: {_container_socket}")
        if _container_socket is None:
            logger.debug("container_socket is None")
            return False

        if not (wait or print_output):
            return True

        if _container_socket.readable():
            # code references the following
            # - https://stackoverflow.com/a/66329671
            # logger.debug("_container_socket is readable")
            _container_socket._sock.setblocking(False)  # type: ignore

            _op = None
            while True:
                try:
                    # Read up-to 10000 bytes.
                    _op = os.read(_container_socket.fileno(), 10000)
                    # logger.debug("Op: {}".format(_op))
                except BlockingIOError as not_ready_error:
                    # logger.exception(not_ready_error)
                    logger.info("waiting...")
                    time.sleep(5)
                    continue

                if _op is None:
                    logger.info("Output not available.")
                    break
                if (
                    _op == b""
                    or (isinstance(_op, bytes) and _op.decode(errors="ignore")) == ""
                ):
                    logger.info("Task finished")
                    break

                # Use print here because console.print has issues decoding output
                if print_output:
                    print(_op.decode(errors="ignore"))
        return True
    except APIError as api_error:
        logger.error(f"APIError: {api_error}")
    return False


# def execute_command_stream(
#     cmd: str,
#     container: Container,
#     wait: bool = True,
#     detach: bool = False,
#     print_output: bool = True,
#     docker_env: Optional[Dict[str, str]] = None,
# ) -> bool:
#     """
#     * https://docker-py.readthedocs.io/en/stable/user_guides/multiplex.html
#     """
#     import os
#     import time
#
#     try:
#         logger.debug("Exec `{}` in container: {}".format(cmd, container.name))
#         _, stream = container.exec_run(
#             cmd=cmd,
#             stdout=True,
#             stdin=True,
#             tty=True,
#             stream=True,
#             demux=False,
#             environment=docker_env,
#         )
#         for data in stream:
#             logger.info(f"data: {data.decode()}")
#     except APIError as api_error:
#         logger.error(f"APIError: {api_error}")
#     return False
