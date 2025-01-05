"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.fireworks import Fireworks
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=Fireworks(id="accounts/fireworks/models/firefunction-v2"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("Whats happening in France?", stream=True)
