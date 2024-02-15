from phi.assistant import Assistant
from phi.llm.openai.like import OpenAILike
from phi.tools.duckduckgo import DuckDuckGo


assistant = Assistant(
    llm=OpenAILike(base_url="http://localhost:1234/v1"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)
assistant.print_response("Whats happening in France? Summarize top stories with sources.", markdown=True)
