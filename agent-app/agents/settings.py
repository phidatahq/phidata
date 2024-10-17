from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    """Agent settings that can be set using environment variables.

    Reference: https://pydantic-docs.helpmanual.io/usage/settings/
    """

    gpt_4: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    default_max_completion_tokens: int = 16000
    default_temperature: float = 0


# Create an AgentSettings object
agent_settings = AgentSettings()
