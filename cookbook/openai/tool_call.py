from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo


assistant = Assistant(llm=OpenAIChat(model="gpt-4-turbo-preview"), tools=[DuckDuckGo()], show_tool_calls=True)
assistant.print_response("Whats happening in France? Summarize top stories with sources.", markdown=True)
