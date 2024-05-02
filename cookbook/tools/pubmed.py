from phi.assistant import Assistant
from phi.tools.pubmed import Pubmed

assistant = Assistant(tools=[Pubmed()], debug=True, show_tool_calls=True)
res = assistant.print_response(
    "ulcerative colitis.",
    markdown=True,
)

print(res)
