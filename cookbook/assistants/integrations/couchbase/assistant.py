import os
import typer
from typing import Optional
from rich.prompt import Prompt

from phi.assistant import Assistant
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.couchbase import CouchbaseVectorDb

bucket_name = "my_bucket"
collection_name = "my_collection"
username = os.getenv("COUCHBASE_USERNAME")
password = os.getenv("COUCHBASE_PASSWORD")
host = os.getenv("COUCHBASE_HOST", "localhost")

vector_db = CouchbaseVectorDb(
    bucket_name=bucket_name,
    collection_name=collection_name,
    username=username,
    password=password,
    host=host,
)

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)

# Comment out after first run
knowledge_base.load(recreate=False, upsert=True)


def couchbase_assistant(user: str = "user"):
    run_id: Optional[str] = None

    assistant = Assistant(
        run_id=run_id,
        user_id=user,
        knowledge_base=knowledge_base,
        use_tools=True,
        show_tool_calls=True,
        debug_mode=True,
        # Uncomment the following line to use traditional RAG
        # add_references_to_prompt=True,
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
        assistant.print_response(message)


if __name__ == "__main__":
    typer.run(couchbase_assistant)
