from phi.assistant import Assistant
from phi.llm.google import Gemini
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(llm=Gemini(model="gemini-1.5-flash"), tools=[DuckDuckGo()], debug_mode=True, show_tool_calls=True)
assistant.print_response("Whats happening in France?", markdown=True, stream=False)
