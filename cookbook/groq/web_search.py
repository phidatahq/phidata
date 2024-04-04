from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.groq import Groq

assistant = Assistant(llm=Groq(model="mixtral-8x7b-32768"), tools=[DuckDuckGo()], show_tool_calls=True, debug_mode=True)
assistant.print_response("Tell me about OpenAI Sora", markdown=True, stream=False)
