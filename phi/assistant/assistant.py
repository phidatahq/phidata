from typing import List, Any, Optional, Dict

from pydantic import BaseModel, ConfigDict, field_validator

from phi.assistant.tool import Tool
from phi.assistant.thread import Thread
from phi.assistant.message import Message
from phi.assistant.row import AssistantRow
from phi.assistant.storage import AssistantStorage
from phi.assistant.exceptions import AssistantIdNotSet
from phi.knowledge.base import KnowledgeBase

from phi.utils.log import logger, set_log_level_to_debug

try:
    from openai import OpenAI
    from openai.types.beta.assistant import Assistant as OpenAIAssistant
    from openai.types.beta.asssitant_deleted import AsssitantDeleted as OpenAIAssistantDeleted
except ImportError:
    logger.error("`openai` not installed")
    raise


class Assistant(BaseModel):
    # -*- LLM settings
    model: str = "gpt-4-1106-preview"
    openai: Optional[OpenAI] = None

    # -*- Assistant settings
    # Assistant id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always assistant.
    object: Optional[str] = None
    # The name of the assistant. The maximum length is 256 characters.
    name: Optional[str] = None
    # The description of the assistant. The maximum length is 512 characters.
    description: Optional[str] = None
    # The system instructions that the assistant uses. The maximum length is 32768 characters.
    instructions: Optional[str] = None

    # -*- Assistant Tools
    # A list of tool enabled on the assistant. There can be a maximum of 128 tools per assistant.
    # Tools can be of types code_interpreter, retrieval, or function.
    tools: Optional[List[Tool | Dict]] = None

    # -*- Assistant Files
    # A list of file IDs attached to this assistant.
    # There can be a maximum of 20 files attached to the assistant.
    # Files are ordered by their creation date in ascending order.
    file_ids: Optional[List[Any]] = None
    # Files attached to this assistant.
    files: Optional[List[Any]] = None

    # -*- Assistant Storage
    storage: Optional[AssistantStorage] = None
    # Create table if it doesn't exist
    create_storage: bool = True
    # AssistantRow from the database: DO NOT SET THIS MANUALLY
    database_row: Optional[AssistantRow] = None

    # -*- Assistant Knowledge Base
    knowledge_base: Optional[KnowledgeBase] = None

    # -*- Thread settings
    # Add an introduction message to the thread
    introduction: Optional[str] = None

    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maxium of 512 characters long.
    metadata: Optional[Dict[str, Any]] = None

    # True if this assistant is active
    is_active: bool = True
    # The Unix timestamp (in seconds) for when the assistant was created.
    created_at: Optional[int] = None

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    openai_assistant: Optional[OpenAIAssistant] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_mode", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @property
    def client(self) -> OpenAI:
        return self.openai or OpenAI()

    def load_from_openai(self, openai_assistant: OpenAIAssistant):
        self.id = openai_assistant.id
        self.object = openai_assistant.object
        self.created_at = openai_assistant.created_at

    def create(self) -> OpenAIAssistant:
        request_body: Dict[str, Any] = {}
        if self.name:
            request_body["name"] = self.name
        if self.description:
            request_body["description"] = self.description
        if self.instructions:
            request_body["instructions"] = self.instructions
        if self.tools:
            _tools = []
            for _tool in self.tools:
                if isinstance(_tool, Tool):
                    _tools.append(_tool.to_dict())
                else:
                    _tools.append(_tool)
            request_body["tools"] = _tools
        if self.file_ids or self.files:
            _file_ids = self.file_ids or []
            # if self.files:
            #     for _file in self.files:
            #         _file_ids.append(_file.get_id())
            request_body["file_ids"] = _file_ids
        if self.metadata:
            request_body["metadata"] = self.metadata

        self.openai_assistant = self.client.beta.assistants.create(
            model=self.model,
            **request_body,
        )
        self.load_from_openai(self.openai_assistant)
        return self.openai_assistant

    def get(self, use_cache: bool = True) -> OpenAIAssistant:
        if self.openai_assistant is not None and use_cache:
            return self.openai_assistant

        _assistant_id = self.id or self.openai_assistant.id if self.openai_assistant else None
        if _assistant_id is not None:
            self.openai_assistant = self.client.beta.assistants.retrieve(
                assistant_id=_assistant_id,
            )
            self.load_from_openai(self.openai_assistant)
            return self.openai_assistant
        raise AssistantIdNotSet("Assistant.id not set")

    def get_or_create(self, use_cache: bool = True) -> OpenAIAssistant:
        try:
            return self.get(use_cache=use_cache)
        except AssistantIdNotSet:
            return self.create()

    def update(self) -> OpenAIAssistant:
        try:
            assistant_to_update = self.get()
            if assistant_to_update is not None:
                request_body: Dict[str, Any] = {}
                if self.name:
                    request_body["name"] = self.name
                if self.description:
                    request_body["description"] = self.description
                if self.instructions:
                    request_body["instructions"] = self.instructions
                if self.tools:
                    _tools = []
                    for _tool in self.tools:
                        if isinstance(_tool, Tool):
                            _tools.append(_tool.to_dict())
                        else:
                            _tools.append(_tool)
                    request_body["tools"] = _tools
                if self.file_ids or self.files:
                    _file_ids = self.file_ids or []
                    # if self.files:
                    #     for _file in self.files:
                    #         _file_ids.append(_file.get_id())
                    request_body["file_ids"] = _file_ids
                if self.metadata:
                    request_body["metadata"] = self.metadata

                self.openai_assistant = self.client.beta.assistants.update(
                    assistant_id=assistant_to_update.id,
                    model=self.model,
                    **request_body,
                )
                self.load_from_openai(self.openai_assistant)
                return self.openai_assistant
        except AssistantIdNotSet:
            logger.warning("Assistant not available")
            raise

    def delete(self) -> OpenAIAssistantDeleted:
        try:
            assistant_to_delete = self.get()
            if assistant_to_delete is not None:
                deletion_status = self.client.beta.assistants.delete(
                    assistant_id=assistant_to_delete.id,
                )
                return deletion_status
        except AssistantIdNotSet:
            logger.warning("Assistant not available")
            raise

    def create_thread(self, thread: Optional[Thread] = None) -> Thread:
        try:
            assistant = self.get()
        except AssistantIdNotSet:
            logger.warning("Assistant not available")
            raise

        if thread is None:
            thread = Thread()
            if self.introduction:
                thread.messages = [
                    Message(
                        role="assistant",
                        content=self.introduction,
                    )
                ]

        thread.assistant_id = assistant.id
        thread.openai_assistant = assistant

        logger.debug(f"Creating thread: {thread}")
        thread.create()
        return thread
