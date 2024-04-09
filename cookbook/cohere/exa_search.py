from phi.assistant import Assistant
from phi.llm.cohere import CohereChat
from phi.tools.exa import ExaTools

assistant = Assistant(llm=CohereChat(model="command-r"), tools=[ExaTools()], show_tool_calls=True)
assistant.cli_app(markdown=True)
