# WARNING! BE CAREFUL UPDATING THIS FILE
# Consider possible security implications associated with subprocess module.
from __future__ import annotations

import subprocess  # nosec


def run_python_snippet(python_executable: str, code_to_run: str) -> str:
    """
    Executes python code by calling python_executable with '-c' option.
    """
    py_exec_cmd = python_executable, "-c", code_to_run

    # subprocess module should never be used with untrusted input
    return subprocess.check_output(  # nosec
        py_exec_cmd,
        shell=False,
        text=True,
    )
