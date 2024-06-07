from phi.assistant import Assistant

assistant = Assistant(
    description="You are a famous short story writer asked to write for a magazine",
    instructions=["You are a pilot on a plane flying from Hawaii to Japan."],
    markdown=True,
    debug_mode=True,
)
assistant.print_response("Tell me a 2 sentence horror story.")
