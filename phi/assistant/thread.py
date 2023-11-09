from typing import Any, Optional, Dict, List

from pydantic import BaseModel, ConfigDict

from phi.assistant.run import Run
from phi.assistant.message import Message
from phi.assistant.assistant import Assistant
from phi.assistant.exceptions import AssistantIdNotSet, ThreadIdNotSet
from phi.utils.log import logger

try:
    from openai import OpenAI
    from openai.types.beta.assistant import Assistant as OpenAIAssistant
    from openai.types.beta.thread import Thread as OpenAIThread
    from openai.types.beta.thread_deleted import ThreadDeleted as OpenAIThreadDeleted
except ImportError:
    logger.error("`openai` not installed")
    raise


class Thread(BaseModel):
    # -*- Thread settings
    # Thread id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always thread.
    object: Optional[str] = None

    # A list of messages in this thread.
    messages: List[Message | Dict] = []

    # Assistant used for this thread
    assistant: Optional[Assistant] = None
    # The ID of the assistant for this thread.
    assistant_id: Optional[str] = None

    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maxium of 512 characters long.
    metadata: Optional[Dict[str, Any]] = None

    # True if this thread is active
    is_active: bool = True
    # The Unix timestamp (in seconds) for when the thread was created.
    created_at: Optional[int] = None

    openai: Optional[OpenAI] = None
    openai_thread: Optional[OpenAIThread] = None
    openai_assistant: Optional[OpenAIAssistant] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def client(self) -> OpenAI:
        return self.openai or OpenAI()

    def load_from_storage(self):
        pass

    def load_from_openai(self, openai_thread: OpenAIThread):
        self.id = openai_thread.id
        self.object = openai_thread.object
        self.created_at = openai_thread.created_at

    def create(self, messages: Optional[List[Message | Dict]] = None) -> "Thread":
        request_body: Dict[str, Any] = {}
        if messages is not None:
            _messages = []
            for _message in messages:
                if isinstance(_message, Message):
                    _messages.append(_message.to_dict())
                else:
                    _messages.append(_message)
            request_body["messages"] = _messages
        if self.metadata is not None:
            request_body["metadata"] = self.metadata

        self.openai_thread = self.client.beta.threads.create(**request_body)
        self.load_from_openai(self.openai_thread)
        logger.debug(f"Thread created: {self.id}")
        return self.openai_thread

    def get_id(self) -> Optional[str]:
        _id = self.id or self.openai_thread.id if self.openai_thread else None
        if _id is None:
            self.load_from_storage()
            _id = self.id
        return _id

    def get(self, use_cache: bool = True) -> "Thread":
        if self.openai_thread is not None and use_cache:
            return self

        _thread_id = self.get_id()
        if _thread_id is None:
            raise ThreadIdNotSet("Thread.id not set")

        self.openai_thread = self.client.beta.threads.retrieve(
            thread_id=_thread_id,
        )
        self.load_from_openai(self.openai_thread)
        return self

    def get_or_create(self, use_cache: bool = True, messages: Optional[List[Message | Dict]] = None) -> "Thread":
        try:
            return self.get(use_cache=use_cache)
        except ThreadIdNotSet:
            return self.create(messages=messages)

    def update(self) -> "Thread":
        try:
            thread_to_update = self.get()
            if thread_to_update is not None:
                request_body: Dict[str, Any] = {}
                if self.metadata is not None:
                    request_body["metadata"] = self.metadata

                self.openai_thread = self.client.beta.threads.update(
                    thread_id=thread_to_update.id,
                    **request_body,
                )
                self.load_from_openai(self.openai_thread)
                logger.debug(f"Thead updated: {self.id}")
                return self
        except ThreadIdNotSet:
            logger.warning("Thread not available")
            raise

    def delete(self) -> OpenAIThreadDeleted:
        try:
            thread_to_delete = self.get()
            if thread_to_delete is not None:
                deletion_status = self.client.beta.threads.delete(
                    thread_id=thread_to_delete.id,
                )
                logger.debug(f"Thread deleted: {self.id}")
                return deletion_status
        except ThreadIdNotSet:
            logger.warning("Thread not available")
            raise

    def add_message(self, message: Message | Dict) -> Message:
        try:
            message = message if isinstance(message, Message) else Message(**message)
        except Exception as e:
            logger.error(f"Error creating Message: {e}")
            raise

        message.thread_id = self.id
        message.create()
        return message

    def add(self, messages: List[Message | Dict]) -> List[Message]:
        existing_thread = self.get_id() is not None
        if existing_thread:
            for message in messages:
                self.add_message(message=message)
        else:
            self.create(messages=messages)
        return self.messages

    def create_run(
        self, assistant_id: Optional[str] = None, run: Optional[Run] = None, use_cache: bool = True, **kwargs
    ) -> Run:
        try:
            thread_to_run = self.get(use_cache=use_cache)
        except ThreadIdNotSet:
            logger.warning("Thread not available")
            raise

        if assistant_id is None:
            assistant_id = self.assistant_id
        if assistant_id is None:
            raise AssistantIdNotSet("Assistant.id not set")

        try:
            if run is None:
                run = Run(**kwargs)
        except Exception as e:
            logger.error(f"Error creating run: {e}")
            raise

        run.thread_id = thread_to_run.id
        run.assistant_id = assistant_id

        logger.debug(f"Creating run: {run}")
        run.create()
        return run

    def get_messages(self, use_cache: bool = True) -> List[Message]:
        try:
            thread_to_read = self.get(use_cache=use_cache)
        except ThreadIdNotSet:
            logger.warning("Thread not available")
            raise

        thread_messages = self.client.beta.threads.messages.list(
            thread_id=thread_to_read.id,
        )
        return [Message(**message.model_dump()) for message in thread_messages]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True, include={"id", "object", "messages", "metadata"})

    def pprint(self):
        """Pretty print using rich"""
        from rich.pretty import pprint

        pprint(self.to_dict())

    def __str__(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=4)
