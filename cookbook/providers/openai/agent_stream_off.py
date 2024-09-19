from rich.pretty import pprint
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    debug_mode=True,
)
agent.print_response("Whats happening in France?", markdown=True, stream=False)

# response = agent.run("Whats happening in France?", markdown=True, stream=False)
#
# pprint(response)
