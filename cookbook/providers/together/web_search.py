from phi.agent import Agent
from phi.model.together import Together
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=Together(), tools=[DuckDuckGo()], show_tool_calls=True)
agent.print_response("Whats happening in France? Summarize top stories with sources.", markdown=True, stream=False)
