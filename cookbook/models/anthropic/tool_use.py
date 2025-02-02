"""Run `pip install duckduckgo-search` to install dependencies."""

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.duckduckgo import DuckDuckGoTools


def sample_tool():
    return "This is a sample tool."


agent = Agent(
    model=Claude(id="claude-3-5-sonnet-20240620"),
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("Whats happening in France?", stream=True)
