from phi.assistant import Assistant

assistant = Assistant(
    system_prompt="Share a 2 sentence story about",
    debug_mode=True,
)
assistant.print_response("Love in the year 12000.")
