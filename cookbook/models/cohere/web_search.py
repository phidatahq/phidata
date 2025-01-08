"""Run `pip install duckduckgo-search` to install dependencies."""

from agno.agent import Agent
from agno.models.cohere import CohereChat
from agno.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=CohereChat(id="command-r-08-2024"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Whats happening in France?", stream=True)
