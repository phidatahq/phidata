from agno.agent import Agent
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.storage.agent.sqlite import SqliteDbAgentStorage
from agno.vectordb.clickhouse import ClickhouseDb

agent = Agent(
    storage=SqliteDbAgentStorage(table_name="recipe_agent"),
    knowledge=PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=ClickhouseDb(
            table_name="recipe_documents",
            host="localhost",
            port=8123,
            username="ai",
            password="ai",
        ),
    ),
    # Show tool calls in the response
    show_tool_calls=True,
    # Enable the agent to search the knowledge base
    search_knowledge=True,
    # Enable the agent to read the chat history
    read_chat_history=True,
)
# Comment out after first run
agent.knowledge.load(recreate=False)  # type: ignore

agent.print_response("How do I make pad thai?", markdown=True)