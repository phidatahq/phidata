from phi.assistant import Assistant
from phi.llm.cohere import Cohere
from phi.tools.exa import ExaTools

assistant = Assistant(llm=Cohere(model="command-r"), tools=[ExaTools()], show_tool_calls=True)
assistant.cli_app(markdown=True)
