from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from phi.memory.classifier import MemoryClassifier
from phi.memory.db import MemoryDb
from phi.memory.manager import MemoryManager
from phi.memory.memory import Memory
from phi.memory.summary import SessionSummary
from phi.memory.summarizer import MemorySummarizer
from phi.model.message import Message
from phi.run.response import RunResponse
from phi.utils.log import logger


class AgentChat(BaseModel):
    message: Optional[Message] = None
    messages: Optional[List[Message]] = None
    response: Optional[RunResponse] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MemoryRetrieval(str, Enum):
    last_n = "last_n"
    first_n = "first_n"
    semantic = "semantic"


class AgentMemory(BaseModel):
    # Chats between the user and agent
    chats: List[AgentChat] = []
    # List of messages sent to the model
    messages: List[Message] = []
    update_system_message_on_change: bool = False

    # Create and store session summaries
    create_session_summary: bool = False
    # Update session summaries after each run
    update_session_summary_after_run: bool = True
    # Summary of the session
    summary: Optional[SessionSummary] = None
    # Summarizer to generate session summaries
    summarizer: Optional[MemorySummarizer] = None

    # Create and store personalized memories for this user
    create_user_memories: bool = False
    # Update memories for the user after each run
    update_user_memories_after_run: bool = True

    # MemoryDb to store personalized memories
    db: Optional[MemoryDb] = None
    # User ID for the personalized memories
    user_id: Optional[str] = None
    retrieval: MemoryRetrieval = MemoryRetrieval.last_n
    memories: Optional[List[Memory]] = None
    num_memories: Optional[int] = None
    classifier: Optional[MemoryClassifier] = None
    manager: Optional[MemoryManager] = None

    # True when memory is being updated
    updating_memory: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        _memory_dict = self.model_dump(
            exclude_none=True,
            exclude={
                "summary",
                "summarizer",
                "db",
                "updating_memory",
                "memories",
                "classifier",
                "manager",
                "retrieval",
            },
        )
        if self.summary:
            _memory_dict["summary"] = self.summary.to_dict()
        if self.memories:
            _memory_dict["memories"] = [memory.to_dict() for memory in self.memories]
        return _memory_dict

    def add_chat(self, agent_chat: AgentChat) -> None:
        """Adds an AgentChat to the chats list."""
        self.chats.append(agent_chat)
        logger.debug("Added AgentChat to AgentMemory")

    def add_system_message(self, message: Message, system_message_role: str = "system") -> None:
        """Add the system messages to the messages list"""
        # If this is the first run in the session, add the system message to the messages list
        if len(self.messages) == 0:
            if message is not None:
                self.messages.append(message)
        # If there are messages in the memory, check if the system message is already in the memory
        # If it is not, add the system message to the messages list
        # If it is, update the system message if content has changed and update_system_message_on_change is True
        else:
            system_message_index = next((i for i, m in enumerate(self.messages) if m.role == system_message_role), None)
            # Update the system message in memory if content has changed
            if system_message_index is not None:
                if (
                    self.messages[system_message_index].content != message.content
                    and self.update_system_message_on_change
                ):
                    logger.info("Updating system message in memory with new content")
                    self.messages[system_message_index] = message
            else:
                # Add the system message to the messages list
                self.messages.insert(0, message)

    def add_message(self, message: Message) -> None:
        """Add a Message to the messages list."""
        self.messages.append(message)
        logger.debug("Added Message to AgentMemory")

    def add_messages(self, messages: List[Message]) -> None:
        """Add a list of messages to the messages list."""
        self.messages.extend(messages)
        logger.debug(f"Added {len(messages)} Messages to AgentMemory")

    def get_messages(self) -> List[Dict[str, Any]]:
        """Returns the messages list as a list of dictionaries."""
        return [message.model_dump(exclude_none=True) for message in self.messages]

    def get_messages_from_last_n_chats(
        self, last_n: Optional[int] = None, skip_role: Optional[str] = None
    ) -> List[Message]:
        """Returns the messages from the last_n chats

        Args:
            last_n: The number of chats to return from the end of the conversation.
            skip_role: Skip messages with this role.

        Returns:
            A list of Messages in the last_n chats.
        """
        if last_n is None:
            logger.debug("Getting messages from all previous chats")
            messages_from_all_history = []
            for prev_chat in self.chats:
                if prev_chat.response and prev_chat.response.messages:
                    if skip_role:
                        prev_chat_messages = [m for m in prev_chat.response.messages if m.role != skip_role]
                    else:
                        prev_chat_messages = prev_chat.response.messages
                    messages_from_all_history.extend(prev_chat_messages)
            logger.debug(f"Messages from previous chats: {len(messages_from_all_history)}")
            return messages_from_all_history

        logger.debug(f"Getting messages from last {last_n} chats")
        messages_from_last_n_history = []
        for prev_chat in self.chats[-last_n:]:
            if prev_chat.response and prev_chat.response.messages:
                if skip_role:
                    prev_chat_messages = [m for m in prev_chat.response.messages if m.role != skip_role]
                else:
                    prev_chat_messages = prev_chat.response.messages
                messages_from_last_n_history.extend(prev_chat_messages)
        logger.debug(f"Messages from last {last_n} chats: {len(messages_from_last_n_history)}")
        return messages_from_last_n_history

    def get_message_pairs(
        self, user_role: str = "user", assistant_role: Optional[List[str]] = None
    ) -> List[Tuple[Message, Message]]:
        """Returns a list of tuples of (user message, assistant response)."""

        if assistant_role is None:
            assistant_role = ["assistant", "model", "CHATBOT"]

        chats_as_message_pairs: List[Tuple[Message, Message]] = []
        for chat in self.chats:
            if chat.response and chat.response.messages:
                user_messages_from_chat = None
                assistant_messages_from_chat = None

                # Start from the beginning to look for the user message
                for message in chat.response.messages:
                    if message.role == user_role:
                        user_messages_from_chat = message
                        break

                # Start from the end to look for the assistant response
                for message in chat.response.messages[::-1]:
                    if message.role in assistant_role:
                        assistant_messages_from_chat = message
                        break

                if user_messages_from_chat and assistant_messages_from_chat:
                    chats_as_message_pairs.append((user_messages_from_chat, assistant_messages_from_chat))
        return chats_as_message_pairs

    def get_tool_calls(self, num_calls: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns a list of tool calls from the messages"""

        tool_calls = []
        for message in self.messages[::-1]:
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_calls.append(tool_call)
                    if num_calls and len(tool_calls) >= num_calls:
                        return tool_calls
        return tool_calls

    def load_user_memories(self) -> None:
        """Load memories from memory db for this user."""
        if self.db is None:
            return

        try:
            if self.retrieval in (MemoryRetrieval.last_n, MemoryRetrieval.first_n):
                memory_rows = self.db.read_memories(
                    user_id=self.user_id,
                    limit=self.num_memories,
                    sort="asc" if self.retrieval == MemoryRetrieval.first_n else "desc",
                )
            else:
                raise NotImplementedError("Semantic retrieval not yet supported.")
        except Exception as e:
            logger.debug(f"Error reading memory: {e}")
            return

        # Clear the existing memories
        self.memories = []

        # No memories to load
        if memory_rows is None or len(memory_rows) == 0:
            return

        for row in memory_rows:
            try:
                self.memories.append(Memory.model_validate(row.memory))
            except Exception as e:
                logger.warning(f"Error loading memory: {e}")
                continue

    def should_update_memory(self, input: str) -> bool:
        """Determines if a message should be added to the memory db."""

        if self.classifier is None:
            self.classifier = MemoryClassifier()

        self.classifier.existing_memories = self.memories
        classifier_response = self.classifier.run(input)
        if classifier_response == "yes":
            return True
        return False

    async def ashould_update_memory(self, input: str) -> bool:
        """Determines if a message should be added to the memory db."""

        if self.classifier is None:
            self.classifier = MemoryClassifier()

        self.classifier.existing_memories = self.memories
        classifier_response = await self.classifier.arun(input)
        if classifier_response == "yes":
            return True
        return False

    def update_memory(self, input: str, force: bool = False) -> Optional[str]:
        """Creates a memory from a message and adds it to the memory db."""

        if input is None or not isinstance(input, str):
            return "Invalid message content"

        if self.db is None:
            logger.warning("MemoryDb not provided.")
            return "Please provide a db to store memories"

        self.updating_memory = True

        # Check if this user message should be added to long term memory
        should_update_memory = force or self.should_update_memory(input=input)
        logger.debug(f"Update memory: {should_update_memory}")

        if not should_update_memory:
            logger.debug("Memory update not required")
            return "Memory update not required"

        if self.manager is None:
            self.manager = MemoryManager(user_id=self.user_id, db=self.db)

        else:
            self.manager.db = self.db
            self.manager.user_id = self.user_id

        response = self.manager.run(input)
        self.load_user_memories()
        self.updating_memory = False
        return response

    async def aupdate_memory(self, input: str, force: bool = False) -> Optional[str]:
        """Creates a memory from a message and adds it to the memory db."""

        if input is None or not isinstance(input, str):
            return "Invalid message content"

        if self.db is None:
            logger.warning("MemoryDb not provided.")
            return "Please provide a db to store memories"

        self.updating_memory = True

        # Check if this user message should be added to long term memory
        should_update_memory = force or await self.ashould_update_memory(input=input)
        logger.debug(f"Async update memory: {should_update_memory}")

        if not should_update_memory:
            logger.debug("Memory update not required")
            return "Memory update not required"

        if self.manager is None:
            self.manager = MemoryManager(user_id=self.user_id, db=self.db)

        else:
            self.manager.db = self.db
            self.manager.user_id = self.user_id

        response = await self.manager.arun(input)
        self.load_user_memories()
        self.updating_memory = False
        return response

    def update_summary(self) -> Optional[SessionSummary]:
        """Creates a summary of the session"""

        self.updating_memory = True

        if self.summarizer is None:
            self.summarizer = MemorySummarizer()

        self.summary = self.summarizer.run(self.get_message_pairs())
        self.updating_memory = False
        return self.summary

    async def aupdate_summary(self) -> Optional[SessionSummary]:
        """Creates a summary of the session"""

        self.updating_memory = True

        if self.summarizer is None:
            self.summarizer = MemorySummarizer()

        self.summary = await self.summarizer.arun(self.get_message_pairs())
        self.updating_memory = False
        return self.summary

    def clear(self) -> None:
        """Clear the AgentMemory"""

        self.chats = []
        self.messages = []
        self.summary = None
        self.memories = None

    def deep_copy(self, *, update: Optional[Dict[str, Any]] = None) -> "AgentMemory":
        new_memory = self.model_copy(deep=True, update=update)
        # clear the new memory to remove any references to the old memory
        new_memory.clear()
        return new_memory
