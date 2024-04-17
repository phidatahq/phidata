from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.ollama import Hermes

assistant = Assistant(llm=Hermes(model="adrienbrault/nous-hermes2pro:Q8_0"), tools=[DuckDuckGo()], show_tool_calls=True)
assistant.print_response("Whats happening in France?", markdown=True)
