from phi.assistant import Assistant
from phi.llm.openai.like import OpenAILike
from phi.tools.duckduckgo import DuckDuckGo


assistant = Assistant(
    llm=OpenAILike(
        model="phi-2",
        base_url="http://localhost:1234/v1",
        api_key="not-provided",
    ),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)
assistant.print_response("Whats happening in France? Summarize top stories with sources.", markdown=True)
