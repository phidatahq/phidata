from typing import Optional, Dict, Any

from phi.model.message import Message
from phi.model.openai.chat import OpenAIChat


class OpenAILike(OpenAIChat):
    id: str = "not-provided"
    name: str = "OpenAILike"
    api_key: Optional[str] = "not-provided"

    def format_message(self, message: Message, map_system_to_developer: bool = False) -> Dict[str, Any]:
        """
        Format a message into the format expected by OpenAI.

        Args:
            message (Message): The message to format.
            map_system_to_developer (bool, optional): Whether the "system" role is mapped to a "developer" role. Defaults to False.
        Returns:
            Dict[str, Any]: The formatted message.
        """
        return super().format_message(message, map_system_to_developer=map_system_to_developer)
