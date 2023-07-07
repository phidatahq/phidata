import logging


def get_logger(logger_name: str, show_path: bool = False) -> logging.Logger:
    from rich.logging import RichHandler

    # https://rich.readthedocs.io/en/latest/reference/logging.html#rich.logging.RichHandler
    # https://rich.readthedocs.io/en/latest/logging.html#handle-exceptions
    rich_handler = RichHandler(
        show_time=False,
        rich_tracebacks=False,
        show_path=show_path,
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


logger: logging.Logger = get_logger("phi")
