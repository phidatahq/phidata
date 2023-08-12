from typing import Dict, List, Any

from pydantic import BaseModel

from phi.llm.schemas import Message, References


class ConversationHistory(BaseModel):
    # Interaction between the user and the LLM.
    # Messages from the user build the LLM prompt stored in llm_history.
    chat_history: List[Message] = []
    # Prompts sent to the LLM and the LLM responses.
    llm_history: List[Message] = []
    # References from the vector database.
    references: List[References] = []

    def add_user_message(self, message: Message) -> None:
        """Adds a message sent by the user to the chat history."""
        self.chat_history.append(message)

    def add_system_prompt(self, message: Message) -> None:
        """Adds the system prompt sent to the LLM to the LLM history."""
        if len(self.llm_history) == 0:
            self.llm_history.append(message)

    def add_user_prompt(self, message: Message) -> None:
        """Adds the user prompt sent to the LLM to the LLM history."""
        self.llm_history.append(message)

    def add_llm_response(self, message: Message) -> None:
        """Adds the LLM response to the chat history and the LLM history."""
        self.chat_history.append(message)
        self.llm_history.append(message)

    def add_chat_history(self, messages: List[Message]) -> None:
        """Adds a list of messages to the chat history."""
        self.chat_history.extend(messages)

    def add_llm_history(self, messages: List[Message]) -> None:
        """Adds a list of messages to the LLM history."""
        self.llm_history.extend(messages)

    def add_references(self, references: References) -> None:
        """Adds references to the references list."""
        self.references.append(references)

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Returns the chat history as a list of dictionaries."""
        return [message.model_dump(exclude_none=True) for message in self.chat_history]

    def get_llm_history(self) -> List[Dict[str, Any]]:
        """Returns the LLM history as a list of dictionaries."""
        return [message.model_dump(exclude_none=True) for message in self.llm_history]

    def get_formatted_history(self) -> str:
        """Returns a formatted chat history"""
        history = ""
        for message in self.chat_history:
            if message.role == "user":
                history += "\n---\n"
            history += f"{message.role.upper()}: {message.content}\n"
        return history
