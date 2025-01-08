"""Run `pip install duckduckgo-search` to install dependencies."""

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGo

agent = Agent(model=OpenRouter(id="gpt-4o"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
