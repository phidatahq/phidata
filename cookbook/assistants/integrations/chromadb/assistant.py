import typer
from rich.prompt import Prompt
from typing import Optional
import logging  # New import for logging

from phi.assistant import Assistant
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.chroma import ChromaDb


knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=ChromaDb(collection="recipes"),
)

# Comment out after first run
knowledge_base.load(recreate=False)


# Set up logging
logging.basicConfig(filename='assistant_log.txt', level=logging.INFO)  # Log file setup


def pdf_assistant(user: str = "user"):
    run_id: Optional[str] = None

    assistant = Assistant(
        run_id=run_id,
        user_id=user,
        knowledge_base=knowledge_base,
        use_tools=True,
        show_tool_calls=True,
        debug_mode=True,
    )
    if run_id is None:
        run_id = assistant.run_id
        print(f"Started Run: {run_id}\n")
    else:
        print(f"Continuing Run: {run_id}\n")

    while True:
        message = Prompt.ask(f"[bold] :sunglasses: {user} [/bold]")
        if message in ("exit", "bye"):
            break
        response = assistant.print_response(message)  # Capture the response
        logging.info(f"{user}: {message} -> Assistant: {response}")  # Log the interaction


if __name__ == "__main__":
    typer.run(pdf_assistant)
