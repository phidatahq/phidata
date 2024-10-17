import logging


def build_logger(
    logger_name: str,
    log_level: int = logging.INFO,
    show_time: bool = False,
    rich_tracebacks: bool = False,
    tracebacks_show_locals: bool = False,
) -> logging.Logger:
    from rich.logging import RichHandler

    rich_handler = RichHandler(
        show_time=show_time, rich_tracebacks=rich_tracebacks, tracebacks_show_locals=tracebacks_show_locals
    )
    rich_handler.setFormatter(
        logging.Formatter(
            fmt="%(message)s",
            datefmt="[%X]",
        )
    )

    _logger = logging.getLogger(logger_name)
    _logger.addHandler(rich_handler)
    _logger.setLevel(log_level)
    _logger.propagate = False
    return _logger


# Default logger instance
logger: logging.Logger = build_logger("agent-app")
