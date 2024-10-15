from phi.assistant import Assistant
from phi.llm.fireworks import Fireworks
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(llm=Fireworks(), tools=[DuckDuckGo()], show_tool_calls=True)
assistant.print_response("Whats happening in France?", markdown=True, stream=False)
