"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.ollama import Hermes
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=Hermes(id="hermes3"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
