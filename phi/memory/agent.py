from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from phi.agent.chat import AgentChat
from phi.memory.classifier import MemoryClassifier
from phi.memory.db import MemoryDb
from phi.memory.manager import MemoryManager
from phi.memory.memory import Memory
from phi.model.message import Message
from phi.utils.log import logger


class MemoryRetrieval(str, Enum):
    last_n = "last_n"
    first_n = "first_n"
    semantic = "semantic"


class AgentMemory(BaseModel):
    # All messages in this session: system, user, tool and assistant messages.
    messages: List[Message] = []
    # All chats in this session: (user message, agent run_response) pairs.
    chats: List[AgentChat] = []

    # Create summary of the conversation
    summary: Optional[Any] = None

    # Create personalized memories for a user
    # MemoryDb to store the memories
    db: Optional[MemoryDb] = None
    # User ID for the memory
    user_id: Optional[str] = None
    retrieval: MemoryRetrieval = MemoryRetrieval.last_n
    memories: Optional[List[Memory]] = None
    num_memories: Optional[int] = None
    classifier: Optional[MemoryClassifier] = None
    manager: Optional[MemoryManager] = None
    updating: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        _memory_dict = self.model_dump(
            exclude_none=True, exclude={"db", "updating", "memories", "classifier", "manager", "retrieval"}
        )
        if self.memories:
            _memory_dict["memories"] = [memory.to_dict() for memory in self.memories]
        return _memory_dict

    def add_run_message(self, message: Message) -> None:
        """Add a Message to the messages list."""
        self.messages.append(message)
        logger.debug("Added Message to AgentMemory")

    def add_run_messages(self, messages: List[Message]) -> None:
        """Add a list of messages to the messages list."""
        self.messages.extend(messages)
        logger.debug(f"Added {len(messages)} Messages to AgentMemory")

    def get_run_messages(self) -> List[Dict[str, Any]]:
        """Returns the messages list as a list of dictionaries."""
        return [message.model_dump(exclude_none=True) for message in self.messages]

    def add_agent_chat(self, agent_chat: AgentChat) -> None:
        """Adds an AgentChat to the chats list."""
        self.chats.append(agent_chat)
        logger.debug("Added AgentChat to AgentMemory")

    def get_messages_from_last_n_chats(self, last_n: Optional[int] = None) -> List[Message]:
        """Returns the messages from the last_n chats

        :param last_n: The number of chats to return from the end of the conversation.
        :return: A list of Messages in the last_n chats.
        """
        logger.debug("Getting messages from all previous chats")
        if last_n is None:
            messages_from_all_history = []
            for response in self.chats:
                if response.response and response.response.messages:
                    messages_from_all_history.extend(response.response.messages)
            logger.debug(f"Messages from previous chats: {len(messages_from_all_history)}")
            return messages_from_all_history

        logger.debug(f"Getting messages from last {last_n} chats")
        messages_from_last_n_history = []
        for response in self.chats[-last_n:]:
            logger.debug(f"Response: {response}")
            if response.response and response.response.messages:
                messages_from_last_n_history.extend(response.response.messages)
        logger.debug(f"Messages from last {last_n} chats: {len(messages_from_last_n_history)}")
        return messages_from_last_n_history

    def get_chats(self) -> List[Tuple[Message, Message]]:
        """Returns a list of tuples of (user message, assistant response)."""

        all_chats_as_message_tuples: List[Tuple[Message, Message]] = []
        for chat in self.chats:
            if chat.response and chat.response.messages:
                user_messages_from_response = None
                assistant_messages_from_response = None
                for message in chat.response.messages:
                    if message.role == "user":
                        user_messages_from_response = message
                    if message.role == "assistant":
                        assistant_messages_from_response = message
                    if user_messages_from_response and assistant_messages_from_response:
                        all_chats_as_message_tuples.append(
                            (user_messages_from_response, assistant_messages_from_response)
                        )
                        user_messages_from_response = None
                        assistant_messages_from_response = None
        return all_chats_as_message_tuples

    def get_tool_calls(self, num_calls: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns a list of tool calls from the run_messages."""

        tool_calls = []
        for run_message in self.messages[::-1]:
            if run_message.tool_calls:
                for tool_call in run_message.tool_calls:
                    tool_calls.append(tool_call)

        if num_calls:
            return tool_calls[:num_calls]
        return tool_calls

    def load_memory(self) -> None:
        """Load the memory from memory db for this user."""
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

    def update_memory(self, input: str, force: bool = False) -> str:
        """Creates a memory from a message and adds it to the memory db."""

        if input is None or not isinstance(input, str):
            return "Invalid message content"

        if self.db is None:
            logger.warning("MemoryDb not provided.")
            return "Please provide a db to store memories"

        self.updating = True

        # Check if this user message should be added to long term memory
        should_update_memory = force or self.should_update_memory(input=input)
        logger.debug(f"Update memory: {should_update_memory}")

        if not should_update_memory:
            logger.debug("Memory update not required")
            return "Memory update not required"

        if self.manager is None:
            self.manager = MemoryManager(user_id=self.user_id, db=self.db)

        response = self.manager.run(input)
        self.load_memory()
        return response

    def get_memories_for_system_prompt(self) -> Optional[str]:
        if self.memories is None or len(self.memories) == 0:
            return None
        memory_str = "<memory_from_previous_interactions>\n"
        memory_str += "\n".join([f"- {memory.memory}" for memory in self.memories])
        memory_str += "\n</memory_from_previous_interactions>"

        return memory_str

    def clear(self) -> None:
        """Clears the AgentMemory"""

        self.messages = []
        self.chats = []
        self.memories = None
        logger.debug("Agent Memory cleared")
