from typing import List
from subprocess import run, CompletedProcess

from phi.cli.console import print_info
from phi.utils.log import logger


def run_shell_command(args: List[str], display_result: bool = True, display_error: bool = True) -> CompletedProcess:
    logger.debug(f"Running command: {args}")
    result = run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr)
    if result.stdout and display_result:
        print_info(result.stdout)
    if result.stderr and display_error:
        print_info(result.stderr)
    return result
