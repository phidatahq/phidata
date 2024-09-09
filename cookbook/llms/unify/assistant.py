from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.unify import UnifyChat

assistant = Assistant(
    llm=UnifyChat(
        endpoint="gpt-4o@openai", 
        api_key="",  
    ),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
)

assistant.print_response("Five learnings from Bhagwad Geeta?", markdown=True, stream=False)   