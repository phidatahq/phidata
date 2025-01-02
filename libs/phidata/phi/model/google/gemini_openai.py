from os import getenv
from typing import Optional


from phi.model.openai.like import OpenAILike


class GeminiOpenAIChat(OpenAILike):
    """
    Class for interacting with the Gemini API (OpenAI).

    Attributes:
        id (str): The ID of the API.
        name (str): The name of the API.
        provider (str): The provider of the API.
        api_key (Optional[str]): The API key for the xAI API.
        base_url (Optional[str]): The base URL for the xAI API.
    """

    id: str = "gemini-1.5-flash"
    name: str = "Gemini"
    provider: str = "Google"

    api_key: Optional[str] = getenv("GOOGLE_API_KEY", None)
    base_url: Optional[str] = "https://generativelanguage.googleapis.com/v1beta/"
