import typer
from os import getenv
from rich.prompt import Prompt
from typing import Optional, List

from phi.assistant import Assistant
from phi.storage.assistant.singlestore import S2AssistantStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.singlestore import S2VectorDb

from resources import config  # type: ignore

host = getenv("SINGLESTORE_HOST", config["host"])
port = getenv("SINGLESTORE_PORT", config["port"])
username = getenv("SINGLESTORE_USERNAME", config["username"])
password = getenv("SINGLESTORE_PASSWORD", config["password"])
database = getenv("SINGLESTORE_DATABASE", config["database"])
ssl_ca = getenv("SINGLESTORE_SSL_CA", config["ssl_ca"])

db_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?ssl_ca={ssl_ca}&ssl_verify_cert=true"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=S2VectorDb(collection="recipes", schema="phidata", db_url=db_url),
)

storage = S2AssistantStorage(table_name="pdf_assistant", schema="phidata", db_url=db_url)


def pdf_assistant(new: bool = False, user: str = "user"):
    run_id: Optional[str] = None

    if not new:
        existing_run_ids: List[str] = storage.get_all_run_ids(user)
        if len(existing_run_ids) > 0:
            run_id = existing_run_ids[0]

    assistant = Assistant(
        run_id=run_id,
        user_id=user,
        knowledge_base=knowledge_base,
        storage=storage,
        # tool_calls=True adds functions to
        # search the knowledge base and chat history
        use_tools=True,
        show_tool_calls=True,
        # Uncomment the following line to use traditional RAG
        # add_references_to_prompt=True,
        # Uncomment the following line to show debug logs
        # debug_mode=True,
    )
    if run_id is None:
        run_id = assistant.run_id
        print(f"Started Run: {run_id}\n")
    else:
        print(f"Continuing Run: {run_id}\n")

    # Comment out after first run
    # if assistant.knowledge_base:
    #     knowledge_base.load(recreate=False)

    while True:
        message = Prompt.ask(f"[bold] :sunglasses: {user} [/bold]")
        if message in ("exit", "bye"):
            break
        assistant.print_response(message, markdown=True)


if __name__ == "__main__":
    typer.run(pdf_assistant)
