from agno.agent import Agent
from agno.tools.newspaper_tools import NewspaperTools

agent = Agent(tools=[NewspaperTools()])
agent.print_response("Please summarize https://en.wikipedia.org/wiki/Language_model")
