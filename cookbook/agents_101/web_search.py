"""Run `pip install openai duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    markdown=True,
    show_tool_calls=True,
    add_datetime_to_instructions=True,
)
web_agent.print_response("Write a report on the US election", stream=True)
