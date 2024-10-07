from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.aws.claude import Claude

assistant = Assistant(
    llm=Claude(model="anthropic.claude-3-5-sonnet-20240620-v1:0"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    debug_mode=True,
    add_datetime_to_instructions=True,
)
assistant.print_response(
    "Who were the biggest upsets in the NFL? Who were the biggest upsets in College Football?",
    markdown=True,
    stream=False,
)
