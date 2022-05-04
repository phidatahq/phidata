from typing import Dict, Any, Optional, List, Union

from rich.console import Console
from rich.style import Style

from phidata.utils.log import logger
from phidata.types.run_status import RunStatus

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


def print_fix(msg: str) -> None:
    console.print("FIX  : {}".format(msg), style=info_style)


def print_error(msg: Union[str, Exception]) -> None:
    logger.error("{}".format(msg))


def print_warning(msg: Union[str, Exception]) -> None:
    logger.warning(f"{msg}")


def print_dict(_dict: dict) -> None:
    from rich.pretty import pprint

    pprint(_dict)


def get_validation_error_loc(validation_error: Dict[str, Any]) -> Optional[str]:
    if "loc" not in validation_error:
        return None
    return " -> ".join(str(e) for e in validation_error["loc"])


def print_validation_errors(validation_errors: List[Dict[str, Any]]) -> None:
    """
    Pretty prints pydantic validation errors.
    TODO: pydantic validation is known to be buggy for nested models, test this function
    """
    from rich import box
    from rich.table import Column, Table

    table = Table(
        Column(header="Field", justify="center"),
        Column(header="Error", justify="center"),
        Column(header="Context", justify="center"),
        box=box.MINIMAL,
        show_lines=True,
    )

    for err in validation_errors:
        # print("err: {}".format(err))
        error_loc = get_validation_error_loc(err)
        _error_ctx_raw = err.get("ctx")
        error_ctx = (
            "\n".join(f"{k}: {v}" for k, v in _error_ctx_raw.items())
            if _error_ctx_raw is not None and isinstance(_error_ctx_raw, dict)
            else ""
        )
        error_msg = err.get("msg")

        if error_loc is not None:
            table.add_row(error_loc, error_msg, error_ctx)

    if table.row_count > 0:
        console.print(table)


def confirm_yes_no(question, default: str = "yes") -> bool:
    """Ask a yes/no question via raw_input().

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    inp_to_result_map = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n]: "
    elif default == "yes":
        prompt = " [Y/n]: "
    elif default == "no":
        prompt = " [y/N]: "
    else:
        raise ValueError(f"Invalid default answer: {default}")

    choice = console.input(prompt=(question + prompt)).lower()
    if default is not None and choice == "":
        return inp_to_result_map[default]
    elif choice in inp_to_result_map:
        return inp_to_result_map[choice]
    else:
        print_error(f"{choice} invalid")
        return False


def print_run_status_table(
    heading: str, task_run_status: List[RunStatus], min_width: Optional[int] = None
) -> None:
    from rich import box
    from rich.table import Column, Table

    table = Table(
        title=heading,
        box=box.ASCII2,
        show_lines=True,
        min_width=(min_width or 50)
        # title_style=Style(bold=True, underline=True)
    )
    table.add_column(header="Name", justify="center")
    table.add_column(header="Status", justify="center")

    for task in task_run_status:
        if task.success:
            table.add_row(
                task.name, "Success" if task.success else "Fail", style=success_style
            )
        else:
            table.add_row(
                task.name, "Success" if task.success else "Fail", style=fail_style
            )

    if table.row_count > 0:
        console.print("")
        console.print(table)
