from phi.assistant import Assistant
from phi.llm.openrouter import OpenRouter
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(
    llm=OpenRouter(model="openai/gpt-3.5-turbo"), tools=[DuckDuckGo()], show_tool_calls=True, debug_mode=True
)
assistant.print_response("Whats happening in France?", markdown=True, stream=False)
