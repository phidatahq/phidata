from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.cassandra.cassandra import CassandraDb
import os

try:
    from cassandra.cluster import Cluster  # type: ignore
except (ImportError, ModuleNotFoundError):
    raise ImportError(
        "Could not import cassandra-driver python package.Please install it with pip install cassandra-driver."
    )
from phi.embedder.mistral import MistralEmbedder
from phi.model.mistral import MistralChat

cluster = Cluster()
session = cluster.connect("testkeyspace")


knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=CassandraDb(table_name="recipes", keyspace="testkeyspace", session=session, embedder=MistralEmbedder()),
)


knowledge_base.load(recreate=False)  # Comment out after first run

agent = Agent(
    provider=MistralChat(provider="mistral-large-latest", api_key=os.getenv("MISTRAL_API_KEY")),
    knowledge_base=knowledge_base,
    use_tools=True,
    show_tool_calls=True,
)

agent.print_response(
    "what are the health benifits of Khao Niew Dam Piek Maphrao Awn ?", markdown=True, show_full_reasoning=True
)
