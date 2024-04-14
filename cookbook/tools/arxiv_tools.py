from phi.assistant import Assistant
from phi.tools.arxiv import ArxivTools

assistant = Assistant(tools=[ArxivTools()], show_tool_calls=True)
assistant.print_response("Search arxiv for 'language models'", markdown=True)
