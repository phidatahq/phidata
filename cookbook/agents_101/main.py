"""
Main entry point for running all agents
"""

import asyncio
from typing import List
import typer
from rich.console import Console

from .agent_ui import app as ui_app
from .web_search import create_web_agent
from .finance_agent import create_finance_agent
from .rag_agent import create_rag_agent, setup_knowledge_base
from .utils import check_api_keys
from .config import DB_CONFIG

console = Console()
app = typer.Typer()

@app.command()
def run_all():
    """Run all agents in sequence"""
    if not check_api_keys():
        raise typer.Exit(1)

    # Web Search
    console.print("\n[bold green]Running Web Search Agent[/bold green]")
    web_agent = create_web_agent()
    web_agent.print_response("What's the latest tech news?", stream=True)

    # Finance
    console.print("\n[bold green]Running Finance Agent[/bold green]")
    finance_agent = create_finance_agent()
    finance_agent.print_response("Show me AAPL stock analysis", stream=True)

    # RAG
    console.print("\n[bold green]Running RAG Agent[/bold green]")
    knowledge_base = setup_knowledge_base(DB_CONFIG["lancedb"]["uri"])
    rag_agent = create_rag_agent(knowledge_base)
    rag_agent.print_response("What Thai recipes do you know?", stream=True)

@app.command()
def run_ui():
    """Run the Agent UI"""
    from phi.playground import serve_playground_app
    serve_playground_app("agent_ui:app", reload=True)

if __name__ == "__main__":
    app()
