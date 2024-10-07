import os

from phi.assistant import Assistant
from phi.llm.mistral import MistralChat
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(
    llm=MistralChat(
        model="mistral-large-latest",
        api_key=os.environ["MISTRAL_API_KEY"],
    ),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    debug_mode=True,
)
assistant.print_response("Whats happening in France? Summarize top 2 stories", markdown=True, stream=True)
