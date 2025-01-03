from phi.agent import Agent


def initialize_count(agent: Agent) -> str:
    return str(agent.session_state.get("count", 0))


def increment_count(agent: Agent) -> str:
    agent.session_state["count"] += 1
    return str(agent.session_state["count"])


agent = Agent(
    session_state={"count": 0},
    tools=[initialize_count, increment_count],
    instructions="Run the function call 1 by 1 and share when you are done",
    show_tool_calls=True,
)
agent.print_response("Initialize the counter and then increment it 5 times", stream=True, markdown=True)
print(f"Session state: {agent.session_state}")
