from agno.agent import Agent
from agno.models.openai import OpenAIChat


# Initialize White Piece Agent
white_piece_agent = Agent(
    name="white_piece_agent",
    role="You'll be given the chess board with positions of all pieces. You'll have to determine the best legal move for the white piece and checkmate the opponent.",
    model=OpenAIChat(id="gpt-4o-mini"),
)

# Initialize Black Piece Agent
black_piece_agent = Agent(
    name="black_piece_agent",
    role="You'll be given the chess board with positions of all pieces. You'll have to determine the best legal move for the black piece and checkmate the opponent.",
    model=OpenAIChat(id="gpt-4o-mini"),

)

# Initialize Master Agent with Tools
master_agent = Agent(
    name="master_agent",
    instructions=[
        "You'll be given a chess board with positions of all pieces. "
        "You'll have to assign the task to the white piece agent or the black piece agent accordingly. "
        "You'll also have to check if the move that any piece is making is legal. "
        "You'll also have to check for checkmates and stalemates. "
        "You'll also have to update the chess board with the new positions of all pieces after each move."
        "You'll have to continue the game until one of the players wins."
    ],
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
    team=[white_piece_agent, black_piece_agent],
    show_tool_calls=True,
    debug_mode=True,
)

# Define Starting Chess Board
starting_board = """['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],  # Black pieces
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],  # Black pawns
    ['.', '.', '.', '.', '.', '.', '.', '.'],  # Empty row
    ['.', '.', '.', '.', '.', '.', '.', '.'],  # Empty row
    ['.', '.', '.', '.', '.', '.', '.', '.'],  # Empty row
    ['.', '.', '.', '.', '.', '.', '.', '.'],  # Empty row
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],  # White pawns
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],  # White pieces
    """


# Print Initial Chess Board
master_agent.print_response(f"The chess board is {starting_board}, continue the game till one of the players wins", stream=True)
