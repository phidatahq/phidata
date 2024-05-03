from phi.assistant import Assistant
from phi.tools.pubmed import Pubmed

assistant = Assistant(tools=[Pubmed()], debug_mode=True, show_tool_calls=True)
assistant.print_response(
    "ulcerative colitis.",
    markdown=True,
)
