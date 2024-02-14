from phi.assistant import Assistant
from phi.llm.openai.like import OpenAILike

assistant = Assistant(
    llm=OpenAILike(
        model="phi-2",
        base_url="http://localhost:1234/v1",
        api_key="not-provided",
    ),
)
assistant.cli_app(markdown=True)
