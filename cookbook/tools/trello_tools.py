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
