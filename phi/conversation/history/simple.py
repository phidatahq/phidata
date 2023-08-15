from typing import Optional, List

from phi.conversation.history.base import ConversationHistory
from phi.llm.schemas import Message


class SimpleConversationHistory(ConversationHistory):
    """DO NOT USE: DEPRECATED"""

    max_messages: int = 6
    max_tokens: Optional[int] = None
    include_assistant_responses: bool = True

    def get_formatted_history(self, last_n: Optional[int] = None) -> str:
        """Returns a formatted chat history for the LLM prompt"""

        history = ""
        messages_in_history: List[Message] = []
        for message in self.chat_history[::-1]:
            if message.role == "user":
                messages_in_history.insert(0, message)
            if message.role == "assistant" and self.include_assistant_responses:
                messages_in_history.insert(0, message)
            if len(messages_in_history) >= self.max_messages:
                break

        for message in messages_in_history:
            if message.role == "user":
                history += "\n---\n"
            history += f"{message.role.upper()}: {message.content}\n"
        return history
