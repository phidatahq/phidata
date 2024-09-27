from phi.assistant import Assistant
from phi.tools.file import FileTools

assistant = Assistant(tools=[FileTools()], show_tool_calls=True)
assistant.print_response("What is the most advanced LLM currently? Save the answer to a file.", markdown=True)
