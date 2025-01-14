from typing import Optional, Dict, Any

from phi.model.message import Message
from phi.model.openai.chat import OpenAIChat


class OpenAILike(OpenAIChat):
    id: str = "not-provided"
    name: str = "OpenAILike"
    api_key: Optional[str] = "not-provided"

    def format_message(self, message: Message) -> Dict[str, Any]:
        """
        Format a message into the format expected by OpenAI.
        Args:
            message (Message): The message to format.
        Returns:
            Dict[str, Any]: The formatted message.
        """
        if message.role == "user":
            if message.images is not None:
                message = self.add_images_to_message(message=message, images=message.images)

        if message.audio is not None:
            message = self.add_audio_to_message(message=message, audio=message.audio)

        return message.to_dict()
