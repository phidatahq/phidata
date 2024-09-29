import asyncio
from typing import List, Optional

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.spinner import Spinner
from rich.text import Text
from pydantic import BaseModel, Field

from phi.agent import Agent, AgentResponse
from phi.model.openai import OpenAIChat

console = Console()


# Define the Pydantic Model that we expect from the Agent as a structured output
class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(
        ..., description="Genre of the movie. If not available, select action, thriller or romantic comedy."
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")


def display_header(
    message: str,
    style: str = "bold cyan",
    panel_title: Optional[str] = None,
    subtitle: Optional[str] = None,
    border_style: str = "bright_magenta",
):
    """
    Display a styled header inside a panel.
    """
    title = Text(message, style=style)
    panel = Panel(Align.center(title), title=panel_title, subtitle=subtitle, border_style=border_style, padding=(1, 2))
    console.print(panel)


def display_spinner(message: str, style: str = "green"):
    """
    Display a spinner with a message.
    """
    spinner = Spinner("dots", text=message, style=style)
    console.print(spinner)


def display_content(content, title: str = "Content"):
    """
    Display the content using Rich's Pretty.
    """
    pretty_content = Pretty(content, expand_all=True)
    panel = Panel(pretty_content, title=title, border_style="blue", padding=(1, 2))
    console.print(panel)


# Agent with a response_model
movie_agent_1 = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You help people write movie scripts.",
    response_model=MovieScript,
)

# Agent with a response_model and structured_outputs
movie_agent_2 = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"),
    description="You help people write movie scripts.",
    response_model=MovieScript,
    structured_outputs=True,
)


def run_agents():
    try:
        # Running movie_agent_1
        display_header("Running Agent with response_model=MovieScript", panel_title="Agent 1")
        with console.status("Running Agent 1...", spinner="dots"):
            run_movie_agent_1: AgentResponse = movie_agent_1.run("New York")
        display_content(run_movie_agent_1.content, title="Agent 1 Response")

        # Running movie_agent_2
        display_header(
            "Running Agent with response_model=MovieScript and structured_outputs=True", panel_title="Agent 2"
        )
        with console.status("Running Agent 2...", spinner="dots"):
            run_movie_agent_2: AgentResponse = movie_agent_2.run("New York")
        display_content(run_movie_agent_2.content, title="Agent 2 Response")
    except Exception as e:
        console.print(f"[bold red]Error occurred while running agents: {e}[/bold red]")


async def run_agents_async():
    try:
        # Running movie_agent_1 asynchronously
        display_header("Running Agent with response_model=MovieScript (async)", panel_title="Async Agent 1")
        with console.status("Running Agent 1...", spinner="dots"):
            async_run_movie_agent_1: AgentResponse = await movie_agent_1.arun("New York")
        display_content(async_run_movie_agent_1.content, title="Async Agent 1 Response")

        # Running movie_agent_2 asynchronously
        display_header(
            "Running Agent with response_model=MovieScript and structured_outputs=True (async)",
            panel_title="Async Agent 2",
        )
        with console.status("Running Agent 2...", spinner="dots"):
            async_run_movie_agent_2: AgentResponse = await movie_agent_2.arun("New York")
        display_content(async_run_movie_agent_2.content, title="Async Agent 2 Response")
    except Exception as e:
        console.print(f"[bold red]Error occurred while running async agents: {e}[/bold red]")


def main():
    run_agents()

    asyncio.run(run_agents_async())


if __name__ == "__main__":
    main()
