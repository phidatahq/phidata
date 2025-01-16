from typing import Union
import httpx
from phi.tools import Toolkit


class TelegramTools(Toolkit):
    base_url = "https://api.telegram.org"

    def __init__(self, token: str, chat_id: Union[str, int]):
        super().__init__(name="telegram")
        self.token = token
        self.chat_id = chat_id

        if not self.token or not self.chat_id:
            raise ValueError("Token or chat ID not provided.")

        self.register(self.send_message)

    def _call_post_method(self, method, *args, **kwargs):
        return httpx.post(f"{self.base_url}/bot{self.token}/{method}", *args, **kwargs)

    def send_message(self, message: str) -> str:
        """This function sends a message to the chat ID.

        :param message: The message to send.
        :return: The response from the API.
        """
        response = self._call_post_method(
            "sendMessage", json={"chat_id": self.chat_id, "text": message}
        )
        try:
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            return f"An error occurred: {e}"
