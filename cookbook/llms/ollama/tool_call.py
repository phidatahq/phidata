from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.ollama import Ollama


assistant = Assistant(
    llm=Ollama(model="llama3"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)

assistant.print_response("Whats happening in the US?", markdown=True)
