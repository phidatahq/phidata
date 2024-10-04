from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from phi.agent.response import AgentResponse
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
    # All messages handled by the Agent: system, user, tool and assistant messages.
    messages: List[Message] = []
    responses: List[AgentResponse] = []

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
        """Adds a Message to the messages list."""
        self.messages.append(message)
        logger.debug("Added Message to memory")

    def add_run_messages(self, messages: List[Message]) -> None:
        """Adds a list of messages to the run_messages."""
        self.messages.extend(messages)
        logger.debug(f"Added {len(messages)} Messages to memory")

    def get_run_messages(self) -> List[Dict[str, Any]]:
        """Returns the run_messages as a list of dictionaries."""
        return [message.model_dump(exclude_none=True) for message in self.messages]

    def add_agent_response(self, response: AgentResponse) -> None:
        """Adds an AgentResponse to the responses list."""
        self.responses.append(response)
        logger.debug("Added AgentResponse to memory")

    def get_messages_from_last_n_responses(self, last_n: Optional[int] = None) -> List[Message]:
        """Returns the messages from the last_n responses

        :param last_n: The number of responses to return from the end of the conversation.
        :return: A list of Messages in the last_n responses.
        """
        if last_n is None:
            return [message for response in self.responses for message in response.messages]

        logger.info(f"Getting messages from last {last_n} responses")
        messages_from_last_n_responses = []
        for response in self.responses[-last_n:]:
            logger.debug(f"Response: {response}")
            if response.response and response.response.messages:
                messages_from_last_n_responses.extend(response.response.messages)
        logger.info(f"Messages from last {last_n} responses: {len(messages_from_last_n_responses)}")
        return messages_from_last_n_responses

    def get_chats(self) -> List[Tuple[Message, Message]]:
        """Returns a list of tuples of user messages and LLM responses."""

        all_chats: List[Tuple[Message, Message]] = []
        current_chat: List[Message] = []

        # Make a copy of the chat_history and remove all system messages from the beginning.
        chat_history = self.chat_history.copy()
        while len(chat_history) > 0 and chat_history[0].role in ("system", "assistant"):
            chat_history = chat_history[1:]

        for m in chat_history:
            if m.role == "system":
                continue
            if m.role == "user":
                # This is a new chat record
                if len(current_chat) == 2:
                    all_chats.append((current_chat[0], current_chat[1]))
                    current_chat = []
                current_chat.append(m)
            if m.role == "assistant":
                current_chat.append(m)

        if len(current_chat) >= 1:
            all_chats.append((current_chat[0], current_chat[1]))
        return all_chats

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
        self.responses = []
        self.memories = None
        logger.debug("Agent Memory cleared")
