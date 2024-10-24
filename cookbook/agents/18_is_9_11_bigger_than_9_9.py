from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.calculator import Calculator

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[Calculator(add=True, subtract=True, multiply=True, divide=True)],
    instructions=["Use the calculator tool for comparisons."],
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("Is 9.11 bigger than 9.9?")
agent.print_response("9.11 and 9.9 -- which is bigger?")
