from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(llm=OpenAIChat(model="gpt-4o"), tools=[DuckDuckGo()], show_tool_calls=True)
assistant.print_response("Share 3 news stories from France", markdown=True)
