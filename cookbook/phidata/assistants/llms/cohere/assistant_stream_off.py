from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.cohere import CohereChat

assistant = Assistant(
    llm=CohereChat(model="command-r"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)
assistant.print_response("Whats happening in France?", markdown=True, stream=False)
