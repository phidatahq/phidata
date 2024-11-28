from typing import Iterator

from phi.agent import Agent
from phi.tools import tool, FunctionCall, AgentRetry

num_calls = 0


def pre_hook(function_call: FunctionCall):
    global num_calls

    print(f"Pre-hook: {function_call.function.name}")
    print(f"Arguments: {function_call.arguments}")
    num_calls += 1
    if num_calls < 2:
        raise AgentRetry("This wasnt interesting enough, please retry with a different argument")


@tool(pre_hook=pre_hook)
def print_something(something: str) -> Iterator[str]:
    print(something)
    yield f"I have printed {something}"


agent = Agent(tools=[print_something], markdown=True)
agent.print_response("Print something interesting", stream=True)
