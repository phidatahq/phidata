from phi.assistant import Assistant
from phi.llm.anyscale import Anyscale
from phi.tools.duckduckgo import DuckDuckGo


assistant = Assistant(llm=Anyscale(), tools=[DuckDuckGo()], show_tool_calls=True, debug_mode=True)
assistant.print_response("Whats happening in France? Summarize top stories with sources.", markdown=True)
