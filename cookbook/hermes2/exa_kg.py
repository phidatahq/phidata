from phi.assistant import Assistant
from phi.tools.exa import ExaTools
from phi.tools.website import WebsiteTools
from phi.llm.ollama import Hermes

assistant = Assistant(
    llm=Hermes(model="adrienbrault/nous-hermes2pro:Q8_0"), tools=[ExaTools(), WebsiteTools()], show_tool_calls=True
)
assistant.print_response(
    "produce this table: research chromatic homotopy theory, "
    "access each link in the result outputting the summary for that article, its link, and keywords; "
    "after the table output make conceptual ascii art of the overarching themes and constructions",
    markdown=True,
)
