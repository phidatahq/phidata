from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.calculator import Calculator

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4o"),
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
    instructions=["You can use the available tools to answer questions."],
    show_tool_calls=True,
    markdown=True,
)
assistant.print_response("Is 9.11 bigger than 9.9?")
assistant.print_response("9.11 and 9.9 -- which is bigger?")
