from phi.assistant import Assistant

assistant = Assistant(monitoring=True)

# Stream is True by default
assistant.print_response("Tell me a 2 sentence horror story.")
# Set stream to False
# assistant.print_response("Tell me a 1 sentence horror story.", stream=False)
