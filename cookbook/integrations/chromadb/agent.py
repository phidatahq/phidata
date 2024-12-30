from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.chroma import ChromaDb

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=ChromaDb(collection="recipes"),
)
# Comment out after first run
knowledge_base.load(recreate=False)

agent = Agent(
    knowledge=knowledge_base,
    # Show tool calls in the response
    show_tool_calls=True,
    # Enable the agent to search the knowledge base
    search_knowledge=True,
    # Enable the agent to read the chat history
    read_chat_history=True,
)

agent.print_response("How do I make pad thai?", markdown=True)
