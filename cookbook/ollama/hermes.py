from phi.assistant import Assistant
from phi.llm.ollama import Ollama
from phi.tools.duckduckgo import DuckDuckGo

hermes = Assistant(
    llm=Ollama(model="openhermes", generate_tool_calls_from_json_mode=True),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)
hermes.print_response("Whats happening in France? Summarize top stories with sources.")
