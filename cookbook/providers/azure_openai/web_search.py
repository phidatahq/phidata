"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.azure import AzureOpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=AzureOpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Whats happening in France?", stream=True)
