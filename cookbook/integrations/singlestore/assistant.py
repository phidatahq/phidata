import typer
from typing import Optional
from os import getenv

from sqlalchemy.engine import create_engine

from phi.assistant import Assistant
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.singlestore import S2VectorDb

USERNAME = getenv("SINGLESTORE_USERNAME")
PASSWORD = getenv("SINGLESTORE_PASSWORD")
HOST = getenv("SINGLESTORE_HOST")
PORT = getenv("SINGLESTORE_PORT")
DATABASE = getenv("SINGLESTORE_DATABASE")
SSL_CERT = getenv("SINGLESTORE_SSL_CERT", None)

db_url = f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?charset=utf8mb4"
if SSL_CERT:
    db_url += f"&ssl_ca={SSL_CERT}&ssl_verify_cert=true"

db_engine = create_engine(db_url)

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=S2VectorDb(
        collection="recipes",
        db_engine=db_engine,
        schema=DATABASE,
    ),
)

# Comment out after first run
knowledge_base.load(recreate=False)


def pdf_assistant(user: str = "user"):
    run_id: Optional[str] = None

    assistant = Assistant(
        run_id=run_id,
        user_id=user,
        knowledge_base=knowledge_base,
        # tool_calls=True adds functions to
        # search the knowledge base and chat history
        use_tools=True,
        show_tool_calls=True,
        # Uncomment the following line to use traditional RAG
        # add_references_to_prompt=True,
    )
    if run_id is None:
        run_id = assistant.run_id
        print(f"Started Run: {run_id}\n")
    else:
        print(f"Continuing Run: {run_id}\n")

    while True:
        assistant.cli_app(markdown=True)


if __name__ == "__main__":
    typer.run(pdf_assistant)
