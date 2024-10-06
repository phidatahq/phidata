"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.google import Gemini
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=Gemini(id="gemini-1.5-flash"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
