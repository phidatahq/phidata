from phi.assistant import Assistant
from phi.tools.exa import ExaTools
from phi.tools.website import WebsiteTools
from phi.llm.groq import Groq

assistant = Assistant(
    llm=Groq(model="mixtral-8x7b-32768"), tools=[ExaTools(), WebsiteTools()], show_tool_calls=True
)
assistant.cli_app(markdown=True, stream=False)
