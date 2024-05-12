from phi.assistant import Assistant
from phi.tools.calculator import Calculator

assistant = Assistant(
    tools=[Calculator()],
    show_tool_calls=True,
    markdown=True,
)
assistant.print_response("What is the square root of 16?")
assistant.print_response("What is 5!?")
assistant.print_response("Is 17 a prime number?")
