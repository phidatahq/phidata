import typer
from phi.assistant import Assistant
from phi.llm.ollama import Ollama
from phi.vectordb.singlestore import S2VectorDb
from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.storage.assistant.singlestore import S2AssistantStorage
from resources import config  # type: ignore

db_url = (
    f"mysql+pymysql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
)
storage = S2AssistantStorage(table_name="pdf_assistant", schema=config["database"], db_url=db_url)
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=S2VectorDb(
        collection="recipes",
        schema=config["database"],
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
