import runpy
import functools
from pathlib import Path
from typing import Optional, List

from phi.agent import Agent
from phi.utils.log import logger


@functools.lru_cache(maxsize=None)
def warn() -> None:
    logger.warning("PythonAgent can execute arbitrary code. Do not use without human supervision.")


class PythonAgent(Agent):
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        save_and_run: bool = True,
        read_files: bool = False,
        list_files: bool = False,
        run_directly: bool = False,
        safe_globals: Optional[dict] = None,
        safe_locals: Optional[dict] = None,
    ):
        super().__init__(name="python_agent")

        self.base_dir: Path = base_dir or Path.cwd()

        # Restricted global and local scope
        self.safe_globals: dict = safe_globals or globals()
        self.safe_locals: dict = safe_locals or locals()

        if save_and_run:
            self.register(self.save_to_file_and_run, sanitize_arguments=False)
        if read_files:
            self.register(self.read_file)
        if list_files:
            self.register(self.list_files)
        if run_directly:
            self.register(self.run_python_code, sanitize_arguments=False)

    def save_to_file_and_run(
        self, file_name: str, code: str, variable_to_return: Optional[str] = None, overwrite: bool = True
    ) -> str:
        """This function saves Python code to a file called `file_name` and then runs it.
        If successful, returns the value of `variable_to_return` if provided otherwise returns the file name.
        If failed, returns an error message.

        :param file_name: The name of the file the code will be saved to.
        :param code: The code to save and run.
        :param variable_to_return: The variable to return.
        :param overwrite: Overwrite the file if it already exists.
        :return: if run is successful, the value of `variable_to_return` if provided else file name.
        """
        try:
            warn()
            file_path = self.base_dir.joinpath(file_name)
            logger.debug(f"Saving code to {file_path}")
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.exists() and not overwrite:
                return f"File {file_name} already exists"
            file_path.write_text(code)
            logger.info(f"Saved: {file_path}")
            logger.info(f"Running {file_path}")
            globals_after_run = runpy.run_path(str(file_path), init_globals=self.safe_globals, run_name="__main__")

            if variable_to_return:
                variable_value = globals_after_run.get(variable_to_return)
                if variable_value is None:
                    return f"Variable {variable_to_return} not found"
                logger.debug(f"Variable {variable_to_return} value: {variable_value}")
                return str(variable_value)
            else:
                return str(file_name)
        except Exception as e:
            logger.error(f"Error saving and running code: {e}")
            return f"Error saving and running code: {e}"

    def read_file(self, file_name: str) -> str:
        """Reads the contents of the file `file_name` and returns the contents if successful.

        :param file_name: The name of the file to read.
        :return: The contents of the file if successful, otherwise returns an error message.
        """
        try:
            logger.info(f"Reading file: {file_name}")
            file_path = self.base_dir.joinpath(file_name)
            contents = file_path.read_text()
            return str(contents)
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return f"Error reading file: {e}"

    def list_files(self) -> List[str]:
        """Returns a list of files in the base directory

        :return: The contents of the file if successful, otherwise returns an error message.
        """
        try:
            logger.info(f"Reading files in : {self.base_dir}")
            return [str(file_path) for file_path in self.base_dir.iterdir()]
        except Exception as e:
            logger.error(f"Error reading files: {e}")
            return [f"Error reading files: {e}"]

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
