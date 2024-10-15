"""Run `pip install duckduckgo-search` to install dependencies."""

import os

from phi.agent import Agent
from phi.model.mistral import MistralChat
from phi.tools.duckduckgo import DuckDuckGo

mistral_api_key = os.getenv("MISTRAL_API_KEY")

agent = Agent(
    model=MistralChat(
        id="mistral-large-latest",
        api_key=mistral_api_key,
    ),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Whats happening in France?", stream=True)
