from agno.agent import Agent
from agno.tools.serpapi_tools import SerpApiTools

agent = Agent(tools=[SerpApiTools()], show_tool_calls=True)
agent.print_response("Whats happening in the USA?", markdown=True)
