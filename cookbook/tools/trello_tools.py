"""
To use Trello Tools, you need to set up authentication:

1. Get your API Key:
   - Go to https://trello.com/power-ups/admin
   - Create a new workspace or select an existing one

2. Api Key and Secret:
   - On the left side click on API Key
   - Copy the generated API Key and secret

3. Generate Token:
   - On the same page click on option to manually generate a Token
   - Authorize the account and copy the generated Token
"""

from phi.tools.trello_tools import TrelloTools
from phi.agent import Agent


agent = Agent(
    instructions=[
        "You are a Trello management assistant that helps organize and manage Trello boards, lists, and cards",
        "Help users with tasks like:",
        "- Creating and organizing boards, lists, and cards",
        "- Moving cards between lists",
        "- Retrieving board and list information",
        "- Managing card details and descriptions",
        "Always confirm successful operations and provide relevant board/list/card IDs and URLs",
        "When errors occur, provide clear explanations and suggest solutions",
    ],
    tools=[TrelloTools()],
    show_tool_calls=True,
)

agent.print_response(
    "Create a board called ai-agent and inside it create list called todo and doing and inside each of them create card called agent sir ",
    stream=True,
)
