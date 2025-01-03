from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo

# We will search DDG but limit the site to Politifact
agent = Agent(tools=[DuckDuckGo(modifier="site:politifact.com")], show_tool_calls=True)
agent.print_response("Is Taylor Swift promoting energy-saving devices with Elon Musk?", markdown=False)
