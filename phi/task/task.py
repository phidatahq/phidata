from uuid import uuid4
from typing import List, Any, Optional, Dict, Union, Type, Iterator

from pydantic import BaseModel, ConfigDict, field_validator

from phi.memory.conversation import ConversationMemory
from phi.utils.response_iterator import ResponseIterator
from phi.utils.log import logger, set_log_level_to_debug


class Task(BaseModel):
    # -*- Task settings
    # Task UUID
    id: Optional[str] = None
    # Task name
    name: Optional[str] = None

    # -*- Conversation state
    conversation_id: Optional[str] = None
    conversation_memory: Optional[ConversationMemory] = None
    conversation_message: Optional[Union[List[Dict], str]] = None
    conversation_tasks: Optional[List[Dict[str, Any]]] = None
    conversation_responses: List[str] = []
    conversation_response_iterator: ResponseIterator = ResponseIterator()

    # -*- Output Settings
    # Output model for the responses
    output_model: Optional[Union[str, List, Type[BaseModel]]] = None
    # If True, the output is converted into the output_model
    parse_output: bool = True
    # -*- The output of this Task
    output: Optional[Any] = None
    # If True, shows the output of the task in the conversation.run()
    show_output: bool = True

    # If True, enable debug logs
    debug_mode: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_mode", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @property
    def streamable(self) -> bool:
        return False

    def set_task_id(self) -> None:
        if self.id is None:
            self.id = str(uuid4())

    def prepare_task(self) -> None:
        self.set_task_id()

    def run(
        self,
        message: Optional[Union[List[Dict], str]] = None,
        stream: bool = True,
    ) -> Union[Iterator[str], str, BaseModel]:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        _dict = {
            "id": self.id,
            "name": self.name,
            "output": self.output,
        }
        return _dict
