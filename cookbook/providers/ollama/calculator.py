from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.calculator import Calculator

agent = Agent(
    model=Ollama(id="llama3.1"),
    tools=[Calculator(add=True, subtract=True, multiply=True, divide=True)],
    instructions=["Use the calculator tool for comparisons."],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Is 9.11 bigger than 9.9?")
