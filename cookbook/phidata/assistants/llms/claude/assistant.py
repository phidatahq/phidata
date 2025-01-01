from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.anthropic import Claude

assistant = Assistant(
    llm=Claude(model="claude-3-5-sonnet-20240620"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)
assistant.print_response("Whats happening in France", markdown=True)
