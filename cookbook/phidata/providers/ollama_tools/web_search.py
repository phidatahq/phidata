"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.ollama import OllamaTools
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=OllamaTools(id="llama3.1:8b"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
agent.print_response("Whats happening in France?", stream=True)
