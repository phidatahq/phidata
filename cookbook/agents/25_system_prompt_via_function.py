from phi.agent import Agent


def get_system_prompt(agent: Agent) -> str:
    return f"You are {agent.name}! Remember to always include your name in your responses."


agent = Agent(
    name="AgentX",
    system_prompt=get_system_prompt,
    markdown=True,
    show_tool_calls=True,
)
agent.print_response("Who are you?", stream=True)
