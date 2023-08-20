from typing import Dict, List, Any, Optional, Tuple

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
        """Returns the chat history as a list of dictionaries.

        :return: A list of dictionaries representing the chat history.
        """
        return [message.model_dump(exclude_none=True) for message in self.chat_history]

    def get_last_n_messages(self, last_n: Optional[int] = None) -> List[Message]:
        """Returns the last n messages in the chat history.

        :param last_n: The number of messages to return from the end of the conversation.
            If None, returns all messages.
        :return: A list of Messages in the chat history.
        """
        return self.chat_history[-last_n:] if last_n else self.chat_history

    def get_llm_history(self) -> List[Dict[str, Any]]:
        """Returns the LLM history as a list of dictionaries."""
        return [message.model_dump(exclude_none=True) for message in self.llm_history]

    def get_formatted_history(self, last_n: Optional[int] = None) -> str:
        """Returns a formatted chat history"""
        messages = self.get_last_n_messages(last_n)
        if len(messages) == 0:
            return ""

        history = ""
        for message in self.get_last_n_messages(last_n):
            if message.role == "user":
                history += "\n---\n"
            history += f"{message.role.upper()}: {message.content}\n"
        return history

    def get_chats(self) -> List[Tuple[Message, Message]]:
        """Returns a list of tuples of user messages and assistant responses."""

        all_chats: List[Tuple[Message, Message]] = []
        current_chat: List[Message] = []

        # Make a copy of the chat history and remove all system messages from the beginning.
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

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(include={"chat_history", "llm_history", "references"})
