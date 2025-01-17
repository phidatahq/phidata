from agno.agent import Agent
from agno.tools.exa import ExaTools

agent = Agent(
    tools=[ExaTools(include_domains=["cnbc.com", "reuters.com", "bloomberg.com"])],
    show_tool_calls=True,
)
agent.print_response("Search for AAPL news", markdown=True)
