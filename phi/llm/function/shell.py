from typing import List

from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger


class ShellScriptsRegistry(FunctionRegistry):
    def __init__(self):
        super().__init__(name="shell_script_registry")
        self.register(self.run_shell_command)

    def run_shell_command(self, args: List[str]) -> str:
        """Runs a shell command and returns the output or error.

        :param args: The command to run as a list of strings.
        :return: The output of the command.
        """
        logger.info(f"Running shell command: {args}")

        import subprocess

        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        logger.debug("Return code:", result.returncode)
        logger.debug("Have {} bytes in stdout:\n{}".format(len(result.stdout), result.stdout.decode()))
        logger.debug("Have {} bytes in stderr:\n{}".format(len(result.stderr), result.stderr.decode()))

        if result.returncode != 0:
            return f"error: {result.stderr.decode()}"
        return result.stdout.decode()
