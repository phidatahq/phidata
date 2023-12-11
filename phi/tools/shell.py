from typing import List

from phi.tools import ToolRegistry
from phi.utils.log import logger


class ShellTools(ToolRegistry):
    def __init__(self):
        super().__init__(name="shell_tools")
        self.register(self.run_shell_command)

    def run_shell_command(self, args: List[str], tail: int = 100) -> str:
        """Runs a shell command and returns the output or error.

        :param args: The command to run as a list of strings.
        :param tail: The number of lines to return from the output.
        :return: The output of the command.
        """
        logger.info(f"Running shell command: {args}")

        import subprocess

        try:
            result = subprocess.run(args, capture_output=True, text=True)
            logger.debug(f"Result: {result}")
            logger.debug(f"Return code: {result.returncode}")
            if result.returncode != 0:
                return f"Error: {result.stderr}"

            # return only the last n lines of the output
            return "\n".join(result.stdout.split("\n")[-tail:])
        except Exception as e:
            logger.warning(f"Failed to run shell command: {e}")
            return f"Error: {e}"
