from agno.models.google.gemini import Gemini

try:
    from agno.model.google.gemini_openai import GeminiOpenAIChat
except ImportError:

    class GeminiOpenAIChat:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "GeminiOpenAIChat requires the 'openai' library. Please install it via `pip install openai`"
            )
