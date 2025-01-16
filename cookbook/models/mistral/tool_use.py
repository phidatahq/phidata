"""Run `pip install duckduckgo-search` to install dependencies."""

import os

from agno.agent import Agent
from agno.models.mistral import Mistral
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(
    model=Mistral(
        id="mistral-large-latest",
    ),
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Whats happening in France?", stream=True)
