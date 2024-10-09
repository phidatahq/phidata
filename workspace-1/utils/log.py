import logging


def build_logger(logger_name: str) -> logging.Logger:
    from rich.logging import RichHandler

    rich_handler = RichHandler(show_time=False, rich_tracebacks=False, tracebacks_show_locals=False)
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


logger: logging.Logger = build_logger("ai")
