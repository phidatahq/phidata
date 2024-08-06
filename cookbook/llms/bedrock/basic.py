from phi.assistant import Assistant
from phi.llm.aws.claude import Claude
from phi.tools.duckduckgo import DuckDuckGo
assistant = Assistant(
    llm=Claude(),
    description="Fetch the latest stock market news",
    tools=[DuckDuckGo()],
)
assistant.print_response(
    "whats the latest news on stock market",
    markdown=True, 
    stream=False
)
