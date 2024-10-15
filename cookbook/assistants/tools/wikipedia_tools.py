from phi.assistant import Assistant
from phi.tools.wikipedia import WikipediaTools

assistant = Assistant(tools=[WikipediaTools()], show_tool_calls=True)
assistant.print_response("Search wikipedia for 'ai'", markdown=True)
