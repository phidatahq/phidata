from phi.assistant import Assistant
from phi.tools.arxiv_toolkit import ArxivToolkit

assistant = Assistant(tools=[ArxivToolkit()], show_tool_calls=True)
assistant.print_response("Search arxiv for 'language models'", markdown=True)
