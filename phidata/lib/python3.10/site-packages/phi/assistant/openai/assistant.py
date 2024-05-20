import json
from typing import List, Any, Optional, Dict, Union, Callable, Tuple

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from phi.assistant.openai.file import File
from phi.assistant.openai.exceptions import AssistantIdNotSet
from phi.tools import Tool, Toolkit
from phi.tools.function import Function
from phi.utils.log import logger, set_log_level_to_debug

try:
    from openai import OpenAI
    from openai.types.beta.assistant import Assistant as OpenAIAssistantType
    from openai.types.beta.assistant_deleted import AssistantDeleted as OpenAIAssistantDeleted
except ImportError:
    logger.error("`openai` not installed")
    raise


class OpenAIAssistant(BaseModel):
    # -*- LLM settings
    model: str = "gpt-4-1106-preview"
    openai: Optional[OpenAI] = None

    # -*- OpenAIAssistant settings
    # OpenAIAssistant id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always assistant.
    object: Optional[str] = None
    # The name of the assistant. The maximum length is 256 characters.
    name: Optional[str] = None
    # The description of the assistant. The maximum length is 512 characters.
    description: Optional[str] = None
    # The system instructions that the assistant uses. The maximum length is 32768 characters.
    instructions: Optional[str] = None

    # -*- OpenAIAssistant Tools
    # A list of tools provided to the assistant. There can be a maximum of 128 tools per assistant.
    # Tools can be of types code_interpreter, retrieval, or function.
    tools: Optional[List[Union[Tool, Toolkit, Callable, Dict, Function]]] = None
    # -*- Functions available to the OpenAIAssistant to call
    # Functions extracted from the tools which can be executed locally by the assistant.
    functions: Optional[Dict[str, Function]] = None

    # -*- OpenAIAssistant Files
    # A list of file IDs attached to this assistant.
    # There can be a maximum of 20 files attached to the assistant.
    # Files are ordered by their creation date in ascending order.
    file_ids: Optional[List[str]] = None
    # Files attached to this assistant.
    files: Optional[List[File]] = None

    # -*- OpenAIAssistant Storage
    # storage: Optional[AssistantStorage] = None
    # Create table if it doesn't exist
    # create_storage: bool = True
    # AssistantRow from the database: DO NOT SET THIS MANUALLY
    # database_row: Optional[AssistantRow] = None

    # -*- OpenAIAssistant Knowledge Base
    # knowledge_base: Optional[AssistantKnowledge] = None

    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maximum of 512 characters long.
    metadata: Optional[Dict[str, Any]] = None

    # True if this assistant is active
    is_active: bool = True
    # The Unix timestamp (in seconds) for when the assistant was created.
    created_at: Optional[int] = None

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    openai_assistant: Optional[OpenAIAssistantType] = None

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

    @model_validator(mode="after")
    def extract_functions_from_tools(self) -> "OpenAIAssistant":
        if self.tools is not None:
            for tool in self.tools:
                if self.functions is None:
                    self.functions = {}
                if isinstance(tool, Toolkit):
                    self.functions.update(tool.functions)
                    logger.debug(f"Functions from {tool.name} added to OpenAIAssistant.")
                elif isinstance(tool, Function):
                    self.functions[tool.name] = tool
                    logger.debug(f"Function {tool.name} added to OpenAIAssistant.")
                elif callable(tool):
                    f = Function.from_callable(tool)
                    self.functions[f.name] = f
                    logger.debug(f"Function {f.name} added to OpenAIAssistant")
        return self

    def __enter__(self):
        return self.create()

    def __exit__(self, exc_type, exc_value, traceback):
        self.delete()

    def load_from_openai(self, openai_assistant: OpenAIAssistantType):
        self.id = openai_assistant.id
        self.object = openai_assistant.object
        self.created_at = openai_assistant.created_at
        self.file_ids = openai_assistant.file_ids
        self.openai_assistant = openai_assistant

    def get_tools_for_api(self) -> Optional[List[Dict[str, Any]]]:
        if self.tools is None:
            return None

        tools_for_api = []
        for tool in self.tools:
            if isinstance(tool, Tool):
                tools_for_api.append(tool.to_dict())
            elif isinstance(tool, dict):
                tools_for_api.append(tool)
            elif callable(tool):
                func = Function.from_callable(tool)
                tools_for_api.append({"type": "function", "function": func.to_dict()})
            elif isinstance(tool, Toolkit):
                for _f in tool.functions.values():
                    tools_for_api.append({"type": "function", "function": _f.to_dict()})
            elif isinstance(tool, Function):
                tools_for_api.append({"type": "function", "function": tool.to_dict()})
        return tools_for_api

    def create(self) -> "OpenAIAssistant":
        request_body: Dict[str, Any] = {}
        if self.name is not None:
            request_body["name"] = self.name
        if self.description is not None:
            request_body["description"] = self.description
        if self.instructions is not None:
            request_body["instructions"] = self.instructions
        if self.tools is not None:
            request_body["tools"] = self.get_tools_for_api()
        if self.file_ids is not None or self.files is not None:
            _file_ids = self.file_ids or []
            if self.files is not None:
                for _file in self.files:
                    _file = _file.get_or_create()
                    if _file.id is not None:
                        _file_ids.append(_file.id)
            request_body["file_ids"] = _file_ids
        if self.metadata is not None:
            request_body["metadata"] = self.metadata

        self.openai_assistant = self.client.beta.assistants.create(
            model=self.model,
            **request_body,
        )
        self.load_from_openai(self.openai_assistant)
        logger.debug(f"OpenAIAssistant created: {self.id}")
        return self

    def get_id(self) -> Optional[str]:
        return self.id or self.openai_assistant.id if self.openai_assistant else None

    def get_from_openai(self) -> OpenAIAssistantType:
        _assistant_id = self.get_id()
        if _assistant_id is None:
            raise AssistantIdNotSet("OpenAIAssistant.id not set")

        self.openai_assistant = self.client.beta.assistants.retrieve(
            assistant_id=_assistant_id,
        )
        self.load_from_openai(self.openai_assistant)
        return self.openai_assistant

    def get(self, use_cache: bool = True) -> "OpenAIAssistant":
        if self.openai_assistant is not None and use_cache:
            return self

        self.get_from_openai()
        return self

    def get_or_create(self, use_cache: bool = True) -> "OpenAIAssistant":
        try:
            return self.get(use_cache=use_cache)
        except AssistantIdNotSet:
            return self.create()

    def update(self) -> "OpenAIAssistant":
        try:
            assistant_to_update = self.get_from_openai()
            if assistant_to_update is not None:
                request_body: Dict[str, Any] = {}
                if self.name is not None:
                    request_body["name"] = self.name
                if self.description is not None:
                    request_body["description"] = self.description
                if self.instructions is not None:
                    request_body["instructions"] = self.instructions
                if self.tools is not None:
                    request_body["tools"] = self.get_tools_for_api()
                if self.file_ids is not None or self.files is not None:
                    _file_ids = self.file_ids or []
                    if self.files is not None:
                        for _file in self.files:
                            try:
                                _file = _file.get()
                                if _file.id is not None:
                                    _file_ids.append(_file.id)
                            except Exception as e:
                                logger.warning(f"Unable to get file: {e}")
                                continue
                    request_body["file_ids"] = _file_ids
                if self.metadata:
                    request_body["metadata"] = self.metadata

                self.openai_assistant = self.client.beta.assistants.update(
                    assistant_id=assistant_to_update.id,
                    model=self.model,
                    **request_body,
                )
                self.load_from_openai(self.openai_assistant)
                logger.debug(f"OpenAIAssistant updated: {self.id}")
                return self
            raise ValueError("OpenAIAssistant not available")
        except AssistantIdNotSet:
            logger.warning("OpenAIAssistant not available")
            raise

    def delete(self) -> OpenAIAssistantDeleted:
        try:
            assistant_to_delete = self.get_from_openai()
            if assistant_to_delete is not None:
                deletion_status = self.client.beta.assistants.delete(
                    assistant_id=assistant_to_delete.id,
                )
                logger.debug(f"OpenAIAssistant deleted: {deletion_status.id}")
                return deletion_status
        except AssistantIdNotSet:
            logger.warning("OpenAIAssistant not available")
            raise

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(
            exclude_none=True,
            include={
                "name",
                "model",
                "id",
                "object",
                "description",
                "instructions",
                "metadata",
                "tools",
                "file_ids",
                "files",
                "created_at",
            },
        )

    def pprint(self):
        """Pretty print using rich"""
        from rich.pretty import pprint

        pprint(self.to_dict())

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=4)

    def __repr__(self) -> str:
        return f"<OpenAIAssistant name={self.name} id={self.id}>"

    #
    # def run(self, thread: Optional["Thread"]) -> "Thread":
    #     from phi.assistant.openai.thread import Thread
    #
    #     return Thread(assistant=self, thread=thread).run()

    def print_response(self, message: str, markdown: bool = False) -> None:
        """Print a response from the assistant"""

        from phi.assistant.openai.thread import Thread

        thread = Thread()
        thread.print_response(message=message, assistant=self, markdown=markdown)

    def cli_app(
        self,
        user: str = "User",
        emoji: str = ":sunglasses:",
        current_message_only: bool = True,
        markdown: bool = True,
        exit_on: Tuple[str, ...] = ("exit", "bye"),
    ) -> None:
        from rich.prompt import Prompt
        from phi.assistant.openai.thread import Thread

        thread = Thread()
        while True:
            message = Prompt.ask(f"[bold] {emoji} {user} [/bold]")
            if message in exit_on:
                break

            thread.print_response(
                message=message, assistant=self, current_message_only=current_message_only, markdown=markdown
            )
