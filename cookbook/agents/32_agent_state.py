from phi.agent import Agent


def get_user_name(agent: Agent) -> str:
    return agent.session_state.get("name", "Unknown")


Agent(
    session_state={"name": "Hunca Munca"},
    tools=[get_user_name],
).print_response("What is my name?", stream=True, markdown=True)
