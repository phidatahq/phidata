from phi.assistant import Assistant
from phi.tools.exa import ExaTools

assistant = Assistant(tools=[ExaTools()], show_tool_calls=True)
assistant.print_response("Search arxiv for 'language models'", markdown=True)
