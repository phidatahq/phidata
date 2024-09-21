from phi.assistant import Assistant
from phi.tools.firecrawl import FirecrawlTools

assistant = Assistant(tools=[FirecrawlTools()], show_tool_calls=True, markdown=True)
assistant.print_response("Tell me about https://github.com/phidatahq/phidata")
