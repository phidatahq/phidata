from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.website import WebsiteTools
from phi.llm.unify import UnifyChat

assistant = Assistant(
    llm=UnifyChat(
        endpoint="gpt-4o@openai",  
        api_key="", 
    ), 
    tools=[DuckDuckGo(), WebsiteTools()], show_tool_calls=True
)
assistant.print_response(
    "Produce a report about Unify AI. Search for their website. Read both urls and provide a detailed summary along with a unique fact.",
    markdown=True,
)

