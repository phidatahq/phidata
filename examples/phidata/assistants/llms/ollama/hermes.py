from phi.assistant import Assistant
from phi.llm.ollama import Ollama
from phi.tools.duckduckgo import DuckDuckGo

hermes = Assistant(
    llm=Ollama(model="openhermes"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)
hermes.print_response("Whats happening in France? Summarize top stories with sources.", markdown=True)
