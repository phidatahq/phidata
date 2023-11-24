from typing import List, Optional, Dict, Iterator, Callable, Union

from pydantic import BaseModel

from phi.task.task import Task
from phi.utils.log import logger
from phi.utils.timer import Timer


class PythonTask(Task):
    entrypoint: Callable[..., Union[Iterator[str], str, BaseModel]]

    @property
    def streamable(self) -> bool:
        return False

    def run(
        self,
        message: Optional[Union[List[Dict], str]] = None,
        stream: bool = True,
    ) -> Union[Iterator[str], str, BaseModel]:
        try:
            logger.debug(f"Running {self.name}...")
            self.prepare_task()
            timer = Timer()
            timer.start()
            self.output = self.entrypoint(message=message, stream=stream, task=self)
            timer.stop()
            logger.debug(f"Finished {self.name} in {timer.elapsed_time}")
            return self.output
        except Exception as e:
            logger.warning(f"Error running {self.name}: {e}")
            return str(e)
