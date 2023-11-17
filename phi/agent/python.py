import runpy
import functools
from typing import Optional
from tempfile import NamedTemporaryFile

from phi.agent import Agent
from phi.utils.log import logger


@functools.lru_cache(maxsize=None)
def warn() -> None:
    logger.warning("PythonAgent can execute arbitrary code. Do not use without human supervision.")


class PythonAgent(Agent):
    def __init__(self, safe_globals: Optional[dict] = None, safe_locals: Optional[dict] = None):
        super().__init__(name="python_agent")

        # Restricted global and local scope
        self.safe_globals: dict = safe_globals or globals()
        self.safe_locals: dict = safe_locals or locals()
        self.register(self.run_python_code, sanitize_arguments=False)
        self.register(self.save_python_code_to_file_and_run, sanitize_arguments=False)

    def run_python_code(self, code: str, variable_to_return: str) -> str:
        """Function to run Python code.
        Returns the value of `variable_to_return` if successful, otherwise returns an error message.

        :param code: The code to run.
        :param variable_to_return: The variable to return.
        :return: value of `variable_to_return` if successful, otherwise returns an error message.
        """
        try:
            warn()

            logger.debug(f"Running code:\n\n{code}\n\n")
            exec(code, self.safe_globals, self.safe_locals)
            result = self.safe_locals.get(variable_to_return)
            if result is None:
                return f"Variable {variable_to_return} not found"
            logger.debug(f"Result: {result}")
            return str(result)
        except Exception as e:
            logger.error(f"Error running python code: {e}")
            return f"Error running python code: {e}"

    def save_python_code_to_file_and_run(self, code: str, variable_to_return: str) -> str:
        """Function to save Python code to a file, then run it.
        Returns the value of `variable_to_return` if successful, otherwise returns an error message.

        :param code: The code to run.
        :param variable_to_return: The variable to return.
        :return: value of `variable_to_return` if successful, otherwise returns an error message.
        """
        try:
            warn()

            with NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                file_path = f.name
                logger.debug(f"Saving code to {file_path}")
                f.write(code)
                logger.info(f"Running code from {file_path}")
                globals_after_run = runpy.run_path(file_path, init_globals=self.safe_globals, run_name="__main__")
                result = globals_after_run.get(variable_to_return)
                if result is None:
                    return f"Variable {variable_to_return} not found"
                logger.debug(f"Result: {result}")
                return str(result)
        except Exception as e:
            logger.error(f"Error running python code: {e}")
            return f"Error running python code: {e}"
