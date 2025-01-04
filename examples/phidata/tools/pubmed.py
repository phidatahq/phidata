from phi.agent import Agent
from phi.tools.pubmed import PubmedTools

agent = Agent(tools=[PubmedTools()], show_tool_calls=True)
agent.print_response("Tell me about ulcerative colitis.")
