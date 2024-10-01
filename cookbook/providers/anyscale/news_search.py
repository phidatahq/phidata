from phi.agent import Agent
from phi.model.anyscale import Anyscale
from phi.tools.duckduckgo import DuckDuckGo


agent = Agent(
    model=Anyscale(id="mistralai/Mixtral-8x7B-Instruct-v0.1"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    debug_mode=True,
    markdown=True
)

agent.print_response("Whats happening in France? Summarize top stories with sources.")
