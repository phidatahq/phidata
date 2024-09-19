from rich.pretty import pprint
from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.model.anthropic import Claude

agent = Agent(
    model=Claude(model="claude-3-5-sonnet-20240620"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    debug_mode=True,
)
# agent.print_response("Whats happening in France?", markdown=True, stream=False)

response = agent.run("Whats happening in France?", markdown=True, stream=False)

pprint(response)


