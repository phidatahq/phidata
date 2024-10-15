"""Run `pip install duckduckgo-search` to install dependencies."""

import asyncio
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=OpenAIChat(id="gpt-4o"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
asyncio.run(agent.aprint_response("Whats happening in France?", stream=True))
