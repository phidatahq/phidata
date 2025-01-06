from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(tools=[DuckDuckGo()], show_tool_calls=True)
agent.print_response("Whats happening in France?", markdown=True)
