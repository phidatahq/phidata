"""Run `pip install duckduckgo-search` to install dependencies."""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGo

agent = Agent(model=OpenAIChat(id="gpt-4o"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)

agent.print_response("Whats happening in New York?", stream=True)
