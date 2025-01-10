from agno.agent import Agent
from agno.knowledge.pdf import PDFUrlKnowledgeBase
from agno.vectordb.cassandra.cassandra import CassandraDb
import os

try:
    from cassandra.cluster import Cluster  # type: ignore
except (ImportError, ModuleNotFoundError):
    raise ImportError(
        "Could not import cassandra-driver python package.Please install it with pip install cassandra-driver."
    )
from agno.embedder.mistral import MistralEmbedder
from agno.models.mistral import MistralChat

cluster = Cluster()
session = cluster.connect("testkeyspace")


knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=CassandraDb(table_name="recipes", keyspace="testkeyspace", session=session, embedder=MistralEmbedder()),
)


knowledge_base.load(recreate=False)  # Comment out after first run

agent = Agent(
    provider=MistralChat(provider="mistral-large-latest", api_key=os.getenv("MISTRAL_API_KEY")),
    knowledge=knowledge_base,
    use_tools=True,
    show_tool_calls=True,
)

agent.print_response(
    "what are the health benefits of Khao Niew Dam Piek Maphrao Awn ?", markdown=True, show_full_reasoning=True
)
