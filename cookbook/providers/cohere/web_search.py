"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.cohere import CohereChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=CohereChat(id="command-r-08-2024"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Whats happening in France?", stream=True)
