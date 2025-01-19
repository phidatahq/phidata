def enable_debug_mode(enable_traceback: bool = False):
    """Enable debug mode for the agno library.

    Args:
        enable_traceback (bool, optional): If True, also enables detailed traceback
            information. Defaults to False.
    """
    from agno.utils.log import set_log_level_to_debug

    set_log_level_to_debug()
    if enable_traceback:
        import sys

        sys.tracebacklimit = None  # Enable full tracebacks


def disable_debug_mode() -> None:
    """Disable debug mode for the agno library.

    This function resets the logging level to INFO
    """
    from agno.utils.log import set_log_level_to_info

    set_log_level_to_info()
