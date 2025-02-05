from typing import Optional

from agno.agent import Agent
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.qdrant import Qdrant
from qdrant_client import QdrantClient

###### This section is only to load the knowledge base. Skip if your knowledge base was populated elsewhere.
# Initialize vector database connection
vector_db = Qdrant(collection="thai-recipes", path="tmp/qdrant")
# Load the knowledge base
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)
knowledge_base.load(recreate=True)  # Comment out after first run
######


def retriever(
    agent: Agent, query: str, num_documents: Optional[int] = 5, **kwargs
) -> Optional[list[dict]]:
    """
    Custom retriever function to search the vector database for relevant documents.

    Args:
        agent (Agent): The agent instance making the query
        query (str): The search query string
        num_documents (Optional[int]): Number of documents to retrieve (default: 5)
        **kwargs: Additional keyword arguments

    Returns:
        Optional[list[dict]]: List of retrieved documents or None if search fails
    """
    try:
        # Query your vector db here
        # ....
        # We're using vector_db.search() as an example
        return vector_db.search(query, num_documents)
    except Exception as e:
        print(f"Error during vector database search: {str(e)}")
        return None


def main():
    """Main function to demonstrate agent usage."""
    # Initialize agent with custom retriever
    # Remember to set search_knowledge=True to use the retriever
    # search_knowledge=True is default when you add a knowledge base but is needed here
    agent = Agent(
        retriever=retriever,
        search_knowledge=True,
        instructions="Search the knowledge base for information",
        show_tool_calls=True,
    )

    # Example query
    query = "List down the ingredients to make Massaman Gai"
    agent.print_response(query, markdown=True)


if __name__ == "__main__":
    main()
