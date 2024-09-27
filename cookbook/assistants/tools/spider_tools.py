from phi.assistant import Assistant
from phi.tools.spider import SpiderTools

assistant = Assistant(
    tools=[SpiderTools()],
    show_tool_calls=True,
    debug_mode=True,
)

assistant.print_response('Can you scrape the first search result from a search on "news in USA"?', markdown=True)
