"""Run `pip install duckduckgo-search` to install dependencies."""

from agno.agent import Agent
from agno.models.ollama import Hermes
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(model=Hermes(id="hermes3"), tools=[DuckDuckGoTools()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
