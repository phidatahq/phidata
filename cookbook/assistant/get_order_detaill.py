from phi.assistant import Assistant


def get_order_details() -> str:
    return "order for humanoid robot is on the way. estimated delivery in 2-3 days"


print("Without function calling")
assistant = Assistant(system_prompt="Nicely format the response. Use emojis where possible.")
assistant.print_response("Where's my order?", markdown=True)

print("\nWith function calling")
assistant = Assistant(tools=[get_order_details], system_prompt="Nicely format the response. Use emojis where possible.")
assistant.print_response("Where's my order?", markdown=True)
