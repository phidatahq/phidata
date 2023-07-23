from typing import Dict, List, Any

from pydantic import BaseModel

from phi.llm.schemas import Message, References


class LLMHistory(BaseModel):
    chat_history: List[Message] = []
    llm_history: List[Message] = []
    references: List[References] = []

    def add_system_message(self, message: Message) -> None:
        if len(self.llm_history) == 0:
            self.llm_history.append(message)

    def add_chat_history(self, message: Message) -> None:
        self.chat_history.append(message)

    def get_chat_history(self) -> List[Dict[str, Any]]:
        return [message.model_dump(exclude_none=True) for message in self.chat_history]

    def add_llm_history(self, message: Message) -> None:
        self.llm_history.append(message)

    def get_llm_history(self) -> List[Dict[str, Any]]:
        return [message.model_dump(exclude_none=True) for message in self.llm_history]

    def add_references(self, references: References) -> None:
        self.references.append(references)

    def get_formatted_history(self) -> str:
        """Returns a formatted chat history for the LLM prompt"""

        history = ""
        for message in self.chat_history:
            if message.role == "user":
                history += "\n---\n"
            history += f"{message.role.upper()}: {message.content}\n"
        return history
