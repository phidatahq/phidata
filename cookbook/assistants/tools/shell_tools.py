from phi.assistant import Assistant
from phi.tools.shell import ShellTools

assistant = Assistant(tools=[ShellTools()], show_tool_calls=True)
assistant.print_response("Show me the contents of the current directory", markdown=True)
