import typer
from phi.assistant import Assistant
from phi.llm.ollama import Ollama
from phi.vectordb.pgvector import PgVector2
from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.storage.assistant.postgres import PgAssistantStorage
from resources import vector_db  # type: ignore

db_url = vector_db.get_db_connection_local()
storage = PgAssistantStorage(table_name="pdf_assistant", db_url=db_url)
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector2(
        collection="recipes",
        db_url=db_url,
        embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
    ),
)
# Comment after first run to avoid reloading the knowledge base
# knowledge_base.load(recreate=False)


def local_assistant(model: str = "openhermes", debug: bool = False):
    print(f"============= Running: {model} =============")
    Assistant(
        llm=Ollama(model=model),
        storage=storage,
        knowledge_base=knowledge_base,
        add_references_to_prompt=True,
        debug_mode=debug,
    ).cli_app(markdown=True)


if __name__ == "__main__":
    typer.run(local_assistant)
