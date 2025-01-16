from agno.agent import Agent
from agno.models.openai import OpenAI
from agno.tools.calculator import CalculatorTools

agent = Agent(
    model=OpenAI(id="gpt-4o"),
    tools=[CalculatorTools(add=True, subtract=True, multiply=True, divide=True)],
    instructions=["Use the calculator tool for comparisons."],
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("Is 9.11 bigger than 9.9?")
agent.print_response("9.11 and 9.9 -- which is bigger?")
