import logging

from phi.cli.settings import phi_cli_settings
from rich.logging import RichHandler

LOGGER_NAME = "phi"


def get_logger(logger_name: str) -> logging.Logger:
    # https://rich.readthedocs.io/en/latest/reference/logging.html#rich.logging.RichHandler
    # https://rich.readthedocs.io/en/latest/logging.html#handle-exceptions
    rich_handler = RichHandler(
        show_time=False,
        rich_tracebacks=False,
        show_path=True if phi_cli_settings.api_runtime == "dev" else False,
        tracebacks_show_locals=False,
    )
    rich_handler.setFormatter(
        logging.Formatter(
            fmt="%(message)s",
            datefmt="[%X]",
        )
    )

    _logger = logging.getLogger(logger_name)
    _logger.addHandler(rich_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    return _logger


logger: logging.Logger = get_logger(LOGGER_NAME)


def set_log_level_to_debug():
    _logger = logging.getLogger(LOGGER_NAME)
    _logger.setLevel(logging.DEBUG)
