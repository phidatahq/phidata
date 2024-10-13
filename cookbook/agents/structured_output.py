import asyncio
from typing import List, Optional

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.spinner import Spinner
from rich.text import Text
from pydantic import BaseModel, Field

from phi.agent import Agent, RunResponse
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


# Agent that uses JSON mode
json_mode_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You write movie scripts.",
    response_model=MovieScript,
)

# Agent that uses structured outputs
structured_output_agent = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"),
    description="You write movie scripts.",
    response_model=MovieScript,
    structured_outputs=True,
)


# Helper functions to display the output
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


def run_agents():
    try:
        # Running json_mode_agent
        display_header("Running Agent with response_model=MovieScript", panel_title="Agent 1")
        with console.status("Running Agent 1...", spinner="dots"):
            run_json_mode_agent: RunResponse = json_mode_agent.run("New York")
        display_content(run_json_mode_agent.content, title="Agent 1 Response")

        # Running structured_output_agent
        display_header(
            "Running Agent with response_model=MovieScript and structured_outputs=True", panel_title="Agent 2"
        )
        with console.status("Running Agent 2...", spinner="dots"):
            run_structured_output_agent: RunResponse = structured_output_agent.run("New York")
        display_content(run_structured_output_agent.content, title="Agent 2 Response")
    except Exception as e:
        console.print(f"[bold red]Error occurred while running agents: {e}[/bold red]")


async def run_agents_async():
    try:
        # Running json_mode_agent asynchronously
        display_header("Running Agent with response_model=MovieScript (async)", panel_title="Async Agent 1")
        with console.status("Running Agent 1...", spinner="dots"):
            async_run_json_mode_agent: RunResponse = await json_mode_agent.arun("New York")
        display_content(async_run_json_mode_agent.content, title="Async Agent 1 Response")

        # Running structured_output_agent asynchronously
        display_header(
            "Running Agent with response_model=MovieScript and structured_outputs=True (async)",
            panel_title="Async Agent 2",
        )
        with console.status("Running Agent 2...", spinner="dots"):
            async_run_structured_output_agent: RunResponse = await structured_output_agent.arun("New York")
        display_content(async_run_structured_output_agent.content, title="Async Agent 2 Response")
    except Exception as e:
        console.print(f"[bold red]Error occurred while running async agents: {e}[/bold red]")


if __name__ == "__main__":
    run_agents()

    asyncio.run(run_agents_async())
