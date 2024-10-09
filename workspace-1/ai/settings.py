from pydantic_settings import BaseSettings


class AISettings(BaseSettings):
    """LLM settings that can be set using environment variables.

    Reference: https://pydantic-docs.helpmanual.io/usage/settings/
    """

    gpt_4: str = "gpt-4o"
    gpt_4_vision: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    default_max_tokens: int = 1024
    default_temperature: float = 0


# Create AISettings object
ai_settings = AISettings()
