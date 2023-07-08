from rich.console import Console
from rich.style import Style

from phi.utils.log import logger

console = Console()

######################################################
## Styles
# Standard Colors: https://rich.readthedocs.io/en/stable/appendix/colors.html#appendix-colors
######################################################

heading_style = Style(
    color="green",
    bold=True,
    underline=True,
)
subheading_style = Style(
    color="chartreuse3",
    bold=True,
)
success_style = Style(color="chartreuse3")
fail_style = Style(color="red")
error_style = Style(color="red")
info_style = Style()
warn_style = Style(color="magenta")


######################################################
## Print functions
######################################################


def print_heading(msg: str) -> None:
    console.print(msg, style=heading_style)


def print_subheading(msg: str) -> None:
    console.print(msg, style=subheading_style)


def print_horizontal_line() -> None:
    console.rule()


def print_info(msg: str) -> None:
    console.print(msg, style=info_style)


def log_generic_error_msg() -> None:
    logger.error("Something went wrong. Please try again.")


def log_client_error_msg() -> None:
    logger.error("ClientError: Please try again.")


def log_network_error_msg() -> None:
    logger.error("NetworkError: Please check internet connectivity.")


def log_server_error_msg() -> None:
    logger.error("ServerError: Could not reach phidata servers.")


def log_auth_error_msg() -> None:
    logger.error("AuthError: could not authenticate, please run `phi auth`")
