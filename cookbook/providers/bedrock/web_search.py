"""Run `pip install duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.aws.claude import Claude
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=Claude(id="anthropic.claude-3-5-sonnet-20240620-v1:0"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("Whats happening in France?", stream=True)
