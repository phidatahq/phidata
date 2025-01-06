from phi.agent import Agent
from phi.tools.arxiv_toolkit import ArxivToolkit

agent = Agent(tools=[ArxivToolkit()], show_tool_calls=True)
agent.print_response("Search arxiv for 'language models'", markdown=True)
