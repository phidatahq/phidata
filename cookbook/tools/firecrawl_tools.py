from phi.assistant import Assistant
from phi.tools.firecrawl import FirecrawlTools

firecrawl_tools = FirecrawlTools(api_key="", max_length=None)
assistant = Assistant(tools=[firecrawl_tools], show_tool_calls=True)

# You can now use either scrape or crawl by specifying the method
assistant.print_response("Scrape https://www.w3schools.com/python/gloss_python_self.asp.", markdown=True)

# If you want to crawl instead, you can use:
# assistant.print_response("Crawl https://github.com/Ayush0054/flamingo-ai and give me a summary of the repository and its contents.", markdown=True)
