from uuid import uuid4
from typing import List, Any, Optional, Dict, Union, Type, Iterator

from pydantic import BaseModel, ConfigDict, field_validator

from phi.memory.conversation import ConversationMemory
from phi.utils.log import logger, set_log_level_to_debug


class Task(BaseModel):
    # -*- Task settings
    # Task UUID
    id: Optional[str] = None
    # Task name
    name: Optional[str] = None
    # Metadata associated with this task
    meta_data: Optional[Dict[str, Any]] = None

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    # -*- Conversation settings
    conversation_memory: Optional["ConversationMemory"] = None
    conversation_message: Optional[Union[List[Dict], str]] = None

    # -*- Output Settings
    # -*- The output of this Task
    output: Optional[Any] = None
    # Output model for the responses
    output_model: Optional[Union[str, List, Type[BaseModel]]] = None
    # If True, shows the output of the LLM in the conversation.run()
    show_output: bool = True

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_mode", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @property
    def streamable(self) -> bool:
        return self.output_model is None

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
            "meta_data": self.meta_data,
            "output": self.output,
        }
        return _dict
