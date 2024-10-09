from phi.agent import Agent
from phi.tools.pubmed import PubmedTools

agent = Agent(tools=[PubmedTools()], debug_mode=True, show_tool_calls=True)
agent.print_response(
    "ulcerative colitis.",
    markdown=True,
)
