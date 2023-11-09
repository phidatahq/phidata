from typing import List, Any, Optional, Dict, Union, Callable

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from phi.assistant.file import File
from phi.assistant.tool import Tool
from phi.assistant.tool.registry import ToolRegistry
from phi.assistant.row import AssistantRow
from phi.assistant.function import Function, FunctionCall
from phi.assistant.storage import AssistantStorage
from phi.assistant.exceptions import AssistantIdNotSet
from phi.knowledge.base import KnowledgeBase

from phi.utils.log import logger, set_log_level_to_debug

try:
    from openai import OpenAI
    from openai.types.beta.assistant import Assistant as OpenAIAssistant
    from openai.types.beta.assistant_deleted import AssistantDeleted as OpenAIAssistantDeleted
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
    tools: Optional[List[Union[Tool, Dict, Callable, ToolRegistry]]] = None
    # Functions the Assistant may call.
    _function_map: Optional[Dict[str, Function]] = None

    # -*- Assistant Files
    # A list of file IDs attached to this assistant.
    # There can be a maximum of 20 files attached to the assistant.
    # Files are ordered by their creation date in ascending order.
    file_ids: Optional[List[str]] = None
    # Files attached to this assistant.
    files: Optional[List[File]] = None

    # -*- Assistant Storage
    storage: Optional[AssistantStorage] = None
    # Create table if it doesn't exist
    create_storage: bool = True
    # AssistantRow from the database: DO NOT SET THIS MANUALLY
    database_row: Optional[AssistantRow] = None

    # -*- Assistant Knowledge Base
    knowledge_base: Optional[KnowledgeBase] = None

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

    def add_function(self, f: Function) -> None:
        if self._function_map is None:
            self._function_map = {}
        self._function_map[f.name] = f
        logger.debug(f"Added function {f.name} to Assistant")

    @model_validator(mode="after")
    def add_functions_to_assistant(self) -> "Assistant":
        if self.tools is not None:
            for tool in self.tools:
                if callable(tool):
                    f = Function.from_callable(tool)
                    self.add_function(f)
                elif isinstance(tool, ToolRegistry):
                    if self._function_map is None:
                        self._function_map = {}
                    self._function_map.update(tool.functions)
                    logger.debug(f"Tools from {tool.name} added to Assistant.")
        return self

    def load_from_storage(self):
        pass

    def load_from_openai(self, openai_assistant: OpenAIAssistant):
        self.id = openai_assistant.id
        self.object = openai_assistant.object
        self.created_at = openai_assistant.created_at
        self.file_ids = openai_assistant.file_ids
        self.openai_assistant = openai_assistant

    def create(self) -> "Assistant":
        request_body: Dict[str, Any] = {}
        if self.name is not None:
            request_body["name"] = self.name
        if self.description is not None:
            request_body["description"] = self.description
        if self.instructions is not None:
            request_body["instructions"] = self.instructions
        if self.tools is not None:
            _tools = []
            for _tool in self.tools:
                if isinstance(_tool, Tool):
                    _tools.append(_tool.to_dict())
                elif isinstance(_tool, dict):
                    _tools.append(_tool)
                elif callable(_tool):
                    func = Function.from_callable(_tool)
                    _tools.append({"type": "function", "function": func.to_dict()})
                elif isinstance(_tool, ToolRegistry):
                    for _f in _tool.functions.values():
                        _tools.append({"type": "function", "function": _f.to_dict()})
            request_body["tools"] = _tools
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
        logger.debug(f"Assistant created: {self.id}")
        return self

    def get_id(self) -> Optional[str]:
        _id = self.id or self.openai_assistant.id if self.openai_assistant else None
        if _id is None:
            self.load_from_storage()
            _id = self.id
        return _id

    def get_from_openai(self) -> OpenAIAssistant:
        _assistant_id = self.get_id()
        if _assistant_id is None:
            raise AssistantIdNotSet("Assistant.id not set")

        self.openai_assistant = self.client.beta.assistants.retrieve(
            assistant_id=_assistant_id,
        )
        self.load_from_openai(self.openai_assistant)
        return self.openai_assistant

    def get(self, use_cache: bool = True) -> "Assistant":
        if self.openai_assistant is not None and use_cache:
            return self

        self.get_from_openai()
        return self

    def get_or_create(self, use_cache: bool = True) -> "Assistant":
        try:
            return self.get(use_cache=use_cache)
        except AssistantIdNotSet:
            return self.create()

    def update(self) -> "Assistant":
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
                    _tools = []
                    for _tool in self.tools:
                        if isinstance(_tool, Tool):
                            _tools.append(_tool.to_dict())
                        elif isinstance(_tool, dict):
                            _tools.append(_tool)
                        elif callable(_tool):
                            func = Function.from_callable(_tool)
                            _tools.append({"type": "function", "function": func.to_dict()})
                        elif isinstance(_tool, ToolRegistry):
                            for _f in _tool.functions.values():
                                _tools.append({"type": "function", "function": _f.to_dict()})
                    request_body["tools"] = _tools
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
                logger.debug(f"Assistant updated: {self.id}")
                return self
        except AssistantIdNotSet:
            logger.warning("Assistant not available")
            raise

    def delete(self) -> OpenAIAssistantDeleted:
        try:
            assistant_to_delete = self.get_from_openai()
            if assistant_to_delete is not None:
                deletion_status = self.client.beta.assistants.delete(
                    assistant_id=assistant_to_delete.id,
                )
                logger.debug(f"Assistant deleted: {deletion_status.id}")
                return deletion_status
        except AssistantIdNotSet:
            logger.warning("Assistant not available")
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
        import json

        return json.dumps(self.to_dict(), indent=4)

    def get_function_call(self, name: str, arguments: Optional[str] = None) -> Optional[FunctionCall]:
        import json

        logger.debug(f"Getting function {name}. Args: {arguments}")
        if self._function_map is None:
            return None

        function_to_call: Optional[Function] = None
        if name in self._function_map:
            function_to_call = self._function_map[name]
        if function_to_call is None:
            logger.error(f"Function {name} not found")
            return None

        function_call = FunctionCall(function=function_to_call)
        if arguments is not None and arguments != "":
            try:
                if "None" in arguments:
                    arguments = arguments.replace("None", "null")
                if "True" in arguments:
                    arguments = arguments.replace("True", "true")
                if "False" in arguments:
                    arguments = arguments.replace("False", "false")
                _arguments = json.loads(arguments)
            except Exception as e:
                logger.error(f"Unable to decode function arguments {arguments}: {e}")
                return None

            if not isinstance(_arguments, dict):
                logger.error(f"Function arguments {arguments} is not a valid JSON object")
                return None

            try:
                clean_arguments: Dict[str, Any] = {}
                for k, v in _arguments.items():
                    if isinstance(v, str):
                        _v = v.strip().lower()
                        if _v in ("none", "null"):
                            clean_arguments[k] = None
                        elif _v == "true":
                            clean_arguments[k] = True
                        elif _v == "false":
                            clean_arguments[k] = False
                        else:
                            clean_arguments[k] = v.strip()
                    else:
                        clean_arguments[k] = v

                function_call.arguments = clean_arguments
            except Exception as e:
                logger.error(f"Unable to parse function arguments {arguments}: {e}")
                return None

        return function_call
