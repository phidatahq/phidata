from phi.assistant import Assistant
from phi.tools.crawl4ai import Crawl4aiTools

assistant = Assistant(tools=[Crawl4aiTools(max_length=None)], show_tool_calls=True, debug_mode=True)
assistant.print_response("Tell me about https://github.com/phidatahq/phidata.", markdown=True)
