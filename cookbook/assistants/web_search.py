from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(tools=[DuckDuckGo()], show_tool_calls=True, debug_mode=True)
assistant.print_response("Whats happening in France?", markdown=True)
