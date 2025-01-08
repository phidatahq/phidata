"""Run `pip install duckduckgo-search` to install dependencies."""

from agno.agent import Agent
from agno.models.together import Together
from agno.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=Together(id="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("Whats happening in France?", stream=True)
