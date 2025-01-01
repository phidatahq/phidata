"""Run `pip install openai duckduckgo-search agno` to install dependencies."""

from agno.agent import Agent
from agno.model.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGo

web_agent = Agent(
    name="Web Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True,
)
web_agent.print_response("Whats happening in France?", stream=True)
