from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.website import WebsiteTools
from phi.llm.ollama import Hermes

assistant = Assistant(
    llm=Hermes(model="adrienbrault/nous-hermes2pro:Q8_0"), tools=[DuckDuckGo(), WebsiteTools()], show_tool_calls=True
)
assistant.print_response(
    "Produce a report about NousResearch. Search for 3 links, for each link provide a summary and a unique fact. Finally make an ascii art of NousResearch.",
    markdown=True,
)
