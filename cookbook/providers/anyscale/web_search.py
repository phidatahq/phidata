"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.anyscale import Anyscale
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=Anyscale(id="mistralai/Mixtral-8x7B-Instruct-v0.1"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
