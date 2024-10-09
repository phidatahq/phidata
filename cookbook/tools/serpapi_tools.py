from phi.agent import Agent
from phi.tools.serpapi_tools import SerpApiTools

agent = Agent(
    tools=[SerpApiTools()],
    show_tool_calls=True,
    debug_mode=True,
)

agent.print_response("Whats happening in the USA?", markdown=True)
