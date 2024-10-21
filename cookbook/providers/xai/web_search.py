"""Build a Web Search Agent using xAI."""

from phi.agent import Agent
from phi.model.xai import xAI
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=xAI(id="grok-beta"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
