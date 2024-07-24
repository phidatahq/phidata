from phi.assistant import Assistant
from phi.tools.calculator import Calculator

assistant = Assistant(
    tools=[
        Calculator(
            add=True,
            subtract=True,
            multiply=True,
            divide=True,
            exponentiate=True,
            factorial=True,
            is_prime=True,
            square_root=True,
        )
    ],
    show_tool_calls=True,
    markdown=True,
)
assistant.print_response("What is 10*5 then to the power of 2, do it step by step")
assistant.print_response("What is the square root of 16?")
assistant.print_response("What is 10!?")
