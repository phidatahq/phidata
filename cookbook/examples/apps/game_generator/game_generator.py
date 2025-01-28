"""
1. Install dependencies using: `pip install openai agno`
2. Run the script using: `python cookbook/examples/streamlit/game_generator/game_generator.py`
"""

from typing import Optional
import streamlit as st
from pathlib import Path

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.models.anthropic import Claude
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.utils.log import logger
from pydantic import BaseModel, Field

games_dir = Path(__file__).parent.joinpath("games")
games_dir.mkdir(parents=True, exist_ok=True)
game_output_path = games_dir / "game_output_file.html"
game_output_path.unlink(missing_ok=True)

# Initialize the storage
storage = PostgresAgentStorage(
    db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    table_name="game_generator_sessions",
    schema="ai",
)

class GameOutput(BaseModel):
    code: str = Field(..., description="The html5 code for the game")
    instructions: str = Field(..., description="Instructions how to play the game")


def get_game_generator_agent(session_id: Optional[str] = None, model_id: str = "openai:gpt-4o", debug_mode: bool = True) -> Agent:
    """Returns an instance of the Game Generator Agent."""
    provider, model_name = model_id.split(":")

    if provider == "openai":
        model = OpenAIChat(id=model_name)
    elif provider == "google":
        model = Gemini(id=model_name)
    elif provider == "anthropic":
        model = Claude(id=model_name)
    else:
        raise ValueError(f"Unsupported model provider: {provider}")

    return Agent(
        name="Game Developer Agent",
        description="You are a game developer that produces working HTML5 code.",
        model=model,
        instructions=[
            "Create a game based on the user's prompt. "
            "The game should be HTML5, completely self-contained and must be runnable simply by opening on a browser.",
            "Require the user to click a button to start the game.",
            "Ensure the game has an alert that pops up if the user dies and then allows the user to restart or exit the game.",
            "Add full screen mode to the game. Always make the button in the top-left corner of the canvas.",
            "Use user-friendly colors and make the game canvas large enough for the game to be playable on a larger screen.",
            "Ensure the HTML is as stylistically pretty as possible, using modern design principles and aesthetics.",
            "When the user is playing, the up and down arrows should not scroll the page.",
            "Starting the game should not go to full screen mode.",
            "Don't add any instructions inside the HTML code, just the game code.",
        ],
        response_model=GameOutput,
        read_chat_history=True,
        session_id=session_id,
        storage=storage,
        debug_mode=debug_mode,
    )

if __name__ == "__main__":
    agent = get_game_generator_agent()
    response = agent.run({"role": "user", "content": "Generate a simple snake game."})
