from phi.assistant import Assistant
from phi.llm.ollama import Ollama
from phi.vectordb.pgvector import PgVector2
from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFUrlKnowledgeBase

from resources import vector_db  # type: ignore

model = "openhermes"
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector2(
        collection="recipes", db_url=vector_db.get_db_connection_local(), embedder=OllamaEmbedder(model=model)
    ),
)
# knowledge_base.load(recreate=False)

assistant = Assistant(
    llm=Ollama(model=model),
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
    debug_mode=True,
)

assistant.print_response("Got any pad thai?")

# Use this to run a CLI application with multi-turn conversation
# assistant.cli_app()
