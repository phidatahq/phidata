from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(tools=[DuckDuckGo()], show_tool_calls=True, monitoring=True, debug_mode=True)
assistant.print_response("Share 1 story from France?", markdown=True)
assistant.print_response("Share 1 story from UK?", markdown=True)
