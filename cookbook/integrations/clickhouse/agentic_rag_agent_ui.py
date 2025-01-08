"""
1. Run: `./cookbook/run_clickhouse.sh` to start a clickhouse
2. Run: `pip install openai clickhouse-connect 'fastapi[standard]' phidata` to install the dependencies
3. Run: `python cookbook/integrations/clickhouse/agentic_rag_agent_ui.py` to run the agent
"""

from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.model.openai import OpenAIChat
from phi.playground import Playground, serve_playground_app
from phi.storage.agent.sqlite import SqlAgentStorage
from phi.vectordb.clickhouse import ClickhouseDb

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
# Create a knowledge base of PDFs from URLs
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=ClickhouseDb(
        table_name="recipe_documents",
        host="localhost",
        port=8123,
        username="ai",
        password="ai",
    ),
)

rag_agent = Agent(
    name="RAG Agent",
    agent_id="rag-agent",
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge_base,
    # Add a tool to search the knowledge base which enables agentic RAG.
    # This is enabled by default when `knowledge` is provided to the Agent.
    search_knowledge=True,
    # Add a tool to read chat history.
    read_chat_history=True,
    # Store the agent sessions in the `ai.rag_agent_sessions` table
    storage=SqlAgentStorage(table_name="rag_agent_sessions"),
    instructions=[
        "Always search your knowledge base first and use it if available.",
        "Share the page number or source URL of the information you used in your response.",
        "If health benefits are mentioned, include them in the response.",
        "Important: Use tables where possible.",
    ],
    markdown=True,
    # Show tool calls in the response
    show_tool_calls=True,
)

app = Playground(agents=[rag_agent]).get_app()

if __name__ == "__main__":
    # Load the knowledge base: Comment after first run as the knowledge base is already loaded
    knowledge_base.load(upsert=True)
    serve_playground_app("agentic_rag_agent_ui:app", reload=True)
