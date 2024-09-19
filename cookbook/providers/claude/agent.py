from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.model.anthropic import Claude

assistant = Agent(
    model=Claude(model="claude-3-5-sonnet-20240620"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)
assistant.print_response("Whats happening in France", markdown=True)
