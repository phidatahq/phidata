from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.confluence import ConfluenceTools

"""
Example showing how to use the Confluence Tools with Phi.

Requirements:
- Confluence server URL and authentication (username/password or API token)
- pip install atlassian-python-api

Usage:
- Set the following environment variables:
    export CONFLUENCE_SERVER_URL="https://your_confluence_server_url"
    export CONFLUENCE_USERNAME="your_username"
    export CONFLUENCE_PASSWORD="your_password"
    export CONFLUENCE_API_TOKEN="your_api_token"  # optional if using API token auth

- Or provide these values when creating the ConfluenceTools instance
"""

# Initialize the Confluence agent
agent = Agent(
    name="Confluence Agent",
    instructions=[
        """You can assist users by:
        - Retrieving pages by title
        - Creating new pages
        - Updating existing pages
        - Performing advanced searches using Confluence Query Language (CQL)
        Note: Use expand parameter when retrieving pages to get additional information. i.e 'body.storage' or 'version'. dont use if user don't ask for content of page or other additional information.
        Always confirm before making changes to pages."""
    ],
    model=OpenAIChat(id="gpt-4o"),
    tools=[ConfluenceTools()],
    show_tool_calls=True,
    markdown=True,
)

# Example interaction with the Confluence agent
agent.print_response("retrive the page titled 'Coolest Company' in the 'AI' space. and it's content")
