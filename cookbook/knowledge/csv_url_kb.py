from phi.agent import Agent
from phi.knowledge.csv import CSVUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = CSVUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/csvs/employees.csv"],
    vector_db=PgVector(table_name="csv_documents", db_url=db_url),
)
knowledge_base.load(recreate=False)  # Comment out after first run

agent = Agent(
    knowledge_base=knowledge_base,
    search_knowledge=True,
)

agent.print_response("What is the average salary of employees in the Marketing department?", markdown=True)
