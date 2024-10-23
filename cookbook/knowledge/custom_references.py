"""
This cookbook shows how to use a custom function to generate references for RAG.

You can use the custom_references_function to generate references for the RAG model.
The function takes a query and returns a list of references from the knowledge base.
"""

import json
from typing import List, Optional

from phi.agent import Agent
from phi.document import Document
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(table_name="recipes", db_url=db_url),
)
# Comment out after first run
# knowledge_base.load(recreate=False)


def custom_references_function(query: str, **kwargs) -> Optional[str]:
    """Return a list of references from the knowledge base"""
    print(f"-*- Searching for references for query: {query}")
    relevant_docs: List[Document] = knowledge_base.search(query=query, num_documents=5)
    if len(relevant_docs) == 0:
        return None

    return json.dumps([doc.to_dict() for doc in relevant_docs], indent=2)


agent = Agent(
    knowledge_base=knowledge_base,
    # Generate references using a custom function.
    references_function=custom_references_function,
    # Adds references to the prompt.
    add_references_to_prompt=True,
)
agent.print_response("How to make Thai curry?", markdown=True)
