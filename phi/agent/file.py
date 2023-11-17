import runpy
import functools
from pathlib import Path
from typing import Optional

from phi.agent import Agent
from phi.utils.log import logger


@functools.lru_cache(maxsize=None)
def warn() -> None:
    logger.warning("FileAgent can execute arbitrary code. Do not use without human supervision.")


class FileAgent(Agent):
    def __init__(
        self, base_dir: Optional[Path] = None, save_file: bool = True, run_file: bool = True, read_file: bool = True
    ):
        super().__init__(name="file_agent")

        self.base_dir: Path = base_dir or Path.cwd()
        if save_file:
            self.register(self.save_contents_to_file, sanitize_arguments=False)
        if run_file:
            self.register(self.run_python_file)
        if read_file:
            self.register(self.read_contents_from_file)

    def save_contents_to_file(self, contents: str, file_name: str) -> str:
        """Saves the contents to a file called `file_name` and returns the file name if successful.

        :param contents: The contents to save.
        :param file_name: The name of the file to save to.
        :return: The file name if successful, otherwise returns an error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            logger.debug(f"Saving contents to {file_path}")
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(contents)
            logger.info(f"Saved: {file_path}")
            return str(file_name)
        except Exception as e:
            logger.error(f"Error saving to file: {e}")
            return f"Error saving to file: {e}"

    def run_python_file(self, file_name: str, variable_to_return: str) -> str:
        """Runs the Python file `file_name` and returns the value of `variable_to_return` if successful.

        :param file_name: The name of the file to run.
        :param variable_to_return: The variable to return.
        :return: value of `variable_to_return` if successful, otherwise returns an error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            logger.info(f"Running file: {file_path}")
            globals_after_run = runpy.run_path(str(file_path), run_name="__main__")
            result = globals_after_run.get(variable_to_return)
            if result is None:
                return f"Variable {variable_to_return} not found"
            logger.debug(f"Result: {result}")
            return str(result)
        except Exception as e:
            logger.error(f"Error running python file: {e}")
            return f"Error running python file: {e}"

    def read_contents_from_file(self, file_name: str) -> str:
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
