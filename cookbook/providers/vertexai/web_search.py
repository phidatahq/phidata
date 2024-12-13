"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.vertexai import Gemini
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=Gemini(id="gemini-2.0-flash-exp"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
