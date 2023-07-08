from httpx import Response, codes

from phi.cli.console import (
    log_client_error_msg,
    log_auth_error_msg,
    log_server_error_msg,
    log_generic_error_msg,
)


def is_invalid_response(r: Response) -> bool:
    """Returns true if the response is invalid"""

    if r.status_code in (
        codes.UNAUTHORIZED,
        codes.BAD_REQUEST,
    ):
        log_auth_error_msg()
        return True
    if codes.is_client_error(r.status_code):
        log_client_error_msg()
        return True
    if codes.is_server_error(r.status_code):
        log_server_error_msg()
        return True
    if codes.is_error(r.status_code):
        log_generic_error_msg()
        return True
    return False


def is_valid_response(r: Response) -> bool:
    """Returns true if the response is valid"""

    return codes.is_success(r.status_code)
