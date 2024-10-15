"""Run `pip install openai duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    markdown=True,
    show_tool_calls=True,
)
web_agent.print_response("Whats happening in France?", stream=True)
