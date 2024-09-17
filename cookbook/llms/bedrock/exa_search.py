from phi.assistant import Assistant
from phi.tools.exa import ExaTools
from phi.tools.website import WebsiteTools
from phi.llm.aws.claude import Claude

assistant = Assistant(llm=Claude(model="anthropic.claude-3-5-sonnet-20240620-v1:0"), tools=[ExaTools(), WebsiteTools()], show_tool_calls=True)
assistant.print_response(
    "Produce this table: research chromatic homotopy theory."
    "Access each link in the result outputting the summary for that article, its link, and keywords; "
    "After the table output make conceptual ascii art of the overarching themes and constructions",
    markdown=True,
    stream=False,
)
