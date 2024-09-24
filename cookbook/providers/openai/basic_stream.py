from phi.agent import Agent
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(model="gpt-4-turbo"),
    instructions=["Respond in a southern tone"],
    # debug_mode=True,
)


# Return the result as a string
agent.print_response("What is a type 2 civilization? How close are we?", stream=True)  # type: ignore
