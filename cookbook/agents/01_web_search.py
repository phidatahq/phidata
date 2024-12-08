"""Run `pip install openai duckduckgo-search phidata` to install dependencies."""

import os
import logging
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_console():
    """Clears the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear_console()
    
    web_agent = Agent(
        name="Web Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGo()],
        instructions=["Always include sources"],
        show_tool_calls=True,
        markdown=True,
    )
    
    while True:
        # Prompt user for query
        query = input("\nEnter your search query (type 'exit' or 'bye' to quit): ").strip().lower()
        
        # Check if user wants to exit
        if query in ['exit', 'bye']:
            logger.info("Exiting the program. Goodbye!")
            break
        
        if query:  # Only process non-empty queries
            web_agent.print_response(query, stream=True)
        else:
            logger.warning("Please enter a valid query")

if __name__ == "__main__":
    main()
