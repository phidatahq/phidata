from typing import List, Optional, Dict, Iterator, Callable, Union, Any

from pydantic import BaseModel

from phi.task.base import BaseTask
from phi.llm.message import Message
from phi.utils.log import logger
from phi.utils.timer import Timer


class PythonTask(BaseTask):
    entrypoint: Callable[..., Union[Iterator[str], str, BaseModel]]

    @property
    def streamable(self) -> bool:
        return False

    def run(
        self,
        message: Optional[Union[List, Dict, str]] = None,
        messages: Optional[List[Union[Dict, Message]]] = None,
        stream: bool = True,
        **kwargs: Dict[str, Any],
    ) -> Union[Iterator[str], str, BaseModel]:
        try:
            logger.debug(f"Running {self.task_name}...")
            self.prepare_task()
            timer = Timer()
            timer.start()
            self.output = self.entrypoint(message=message, stream=stream, task=self)
            timer.stop()
            logger.debug(f"Finished {self.task_name} in {timer.elapsed_time}")
            return self.output
        except Exception as e:
            logger.warning(f"Error running {self.task_name}: {e}")
            return str(e)
