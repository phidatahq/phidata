from phi.assistant import Assistant
from phi.llm.cohere import CohereChat
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(
    llm=CohereChat(model="command-r"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)
assistant.print_response("Whats happening in France?", markdown=True)
