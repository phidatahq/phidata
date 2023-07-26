from typing import Dict, List, Any

from pydantic import BaseModel

from phi.llm.schemas import Message, References


class LLMHistory(BaseModel):
    # Messages sent by the user and the LLMs responses.
    chat_history: List[Message] = []
    # Prompts sent to the LLM and the LLMs responses.
    llm_history: List[Message] = []
    # References from the vector database.
    references: List[References] = []

    def add_system_prompt(self, message: Message) -> None:
        if len(self.llm_history) == 0:
            self.llm_history.append(message)

    def add_user_question(self, message: Message) -> None:
        self.chat_history.append(message)

    def add_user_prompt(self, message: Message) -> None:
        self.llm_history.append(message)

    def add_llm_response(self, message: Message) -> None:
        self.chat_history.append(message)
        self.llm_history.append(message)

    def add_chat_history(self, messages: List[Message]) -> None:
        self.chat_history.extend(messages)

    def add_llm_history(self, messages: List[Message]) -> None:
        self.llm_history.extend(messages)

    def add_references(self, references: References) -> None:
        self.references.append(references)

    def get_chat_history(self) -> List[Dict[str, Any]]:
        return [message.model_dump(exclude_none=True) for message in self.chat_history]

    def get_llm_history(self) -> List[Dict[str, Any]]:
        return [message.model_dump(exclude_none=True) for message in self.llm_history]

    def get_formatted_history(self) -> str:
        """Returns a formatted chat history for the LLM prompt"""

        history = ""
        for message in self.chat_history:
            if message.role == "user":
                history += "\n---\n"
            history += f"{message.role.upper()}: {message.content}\n"
        return history
