from typing import Any, Optional, Dict, List

from pydantic import BaseModel, ConfigDict

from phi.assistant.run import Run
from phi.assistant.message import Message
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

    # A list of messages to start the thread with.
    messages: Optional[List[Message | Dict]] = None

    # The ID of the assistant for this message.
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

    def load_from_openai(self, openai_thread: OpenAIThread):
        self.id = openai_thread.id
        self.object = openai_thread.object
        self.created_at = openai_thread.created_at

    def create(self) -> OpenAIThread:
        request_body: Dict[str, Any] = {}
        if self.messages:
            _messages = []
            for _message in self.messages:
                if isinstance(_message, Message):
                    _messages.append(_message.to_dict())
                else:
                    _messages.append(_message)
            request_body["messages"] = _messages
        if self.metadata:
            request_body["metadata"] = self.metadata

        self.openai_thread = self.client.beta.threads.create(**request_body)
        self.load_from_openai(self.openai_thread)
        return self.openai_thread

    def get(self, use_cache: bool = True) -> OpenAIThread:
        if self.openai_thread is not None and use_cache:
            return self.openai_thread

        _thread_id = self.id or self.openai_thread.id if self.openai_thread else None
        if _thread_id is not None:
            self.openai_thread = self.client.beta.threads.retrieve(
                thread_id=_thread_id,
            )
            self.load_from_openai(self.openai_thread)
            return self.openai_thread
        raise ThreadIdNotSet("Thread.id not set")

    def get_or_create(self, use_cache: bool = True) -> OpenAIThread:
        try:
            return self.get(use_cache=use_cache)
        except ThreadIdNotSet:
            return self.create()

    def update(self) -> OpenAIThread:
        try:
            thread_to_update = self.get()
            if thread_to_update is not None:
                request_body: Dict[str, Any] = {}
                if self.metadata:
                    request_body["metadata"] = self.metadata

                self.openai_thread = self.client.beta.threads.update(
                    thread_id=thread_to_update.id,
                    **request_body,
                )
                self.load_from_openai(self.openai_thread)
                return self.openai_thread
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
                return deletion_status
        except ThreadIdNotSet:
            logger.warning("Thread not available")
            raise

    def create_message(self, message: Optional[Message] = None, **kwargs) -> Message:
        try:
            if message is None:
                message = Message(**kwargs)
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            raise
        message.thread_id = self.id

        logger.debug(f"Creating message: {message}")
        message.create()
        return message

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
