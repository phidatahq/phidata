"""
Run `pip install duckduckgo-search sqlalchemy pgvector pypdf openai ollama` to install dependencies.

Run Ollama Server: `ollama serve`
Pull required models: 
`ollama pull openhermes`
`ollama pull llama3.1:8b`

If you haven't deployed database yet, run:
`docker run --rm -it -e POSTGRES_PASSWORD=ai -e POSTGRES_USER=ai -e POSTGRES_DB=ai -p 5532:5432 --name postgres pgvector/pgvector:pg17` 
to deploy a PostgreSQL database.

"""

from phi.agent import Agent
from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.model.ollama import OllamaTools
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(
        table_name="recipes",
        db_url=db_url,
        embedder=OllamaEmbedder(host="http://localhost:11434"),
    ),
)
knowledge_base.load(recreate=False)  # Comment out after first run

agent = Agent(
    model=OllamaTools(id="llama3.1:8b"),
    knowledge_base=knowledge_base,
    use_tools=True,
    show_tool_calls=True,
)
agent.print_response("How to make Thai curry?", markdown=True)
