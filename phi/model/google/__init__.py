from phi.model.google.gemini import Gemini

try:
    from phi.model.google.gemini_openai import GeminiOpenAIChat
except ImportError:

    class GeminiOpenAIChat:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "GeminiOpenAIChat requires the 'openai' library. Please install it via `pip install openai`"
            )
