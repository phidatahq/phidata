from agno.agent import Agent
from agno.knowledge.pdf import PDFUrlKnowledgeBase
from agno.vectordb.cassandra.cassandra import CassandraDb
from agno.models.mistral import MistralChat
from agno.embedder.mistral import MistralEmbedder
try:
    from cassandra.cluster import Cluster  # type: ignore
except (ImportError, ModuleNotFoundError):
    raise ImportError(
        "Could not import cassandra-driver python package.Please install it with pip install cassandra-driver."
    )

cluster = Cluster()

session = cluster.connect()
session.execute(
    """
    CREATE KEYSPACE IF NOT EXISTS testkeyspace
    WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 1 }
    """
)

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=CassandraDb(
        table_name="recipes",
        keyspace="testkeyspace", 
        session=session,
        embedder = MistralEmbedder()
    ),
)


knowledge_base.load(recreate=True)  # Comment out after first run

agent = Agent(
    model=MistralChat(),
    knowledge=knowledge_base,
    show_tool_calls=True,
)

agent.print_response(
    "What are the health benefits of Khao Niew Dam Piek Maphrao Awn?", markdown=True, show_full_reasoning=True
)
