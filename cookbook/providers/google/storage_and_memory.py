"""Run `pip install duckduckgo-search pgvector google.generativeai` to install dependencies."""

from phi.agent import Agent
from phi.memory import AgentMemory
from phi.memory.db.postgres import PgMemoryDb
from phi.model.google import Gemini
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.storage.agent.postgres import PgAgentStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(table_name="recipes", db_url=db_url),
)
knowledge_base.load(recreate=True)  # Comment out after first run

agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[DuckDuckGo()],
    knowledge=knowledge_base,
    storage=PgAgentStorage(table_name="agent_sessions", db_url=db_url),
    # Store the memories and summary in a database
    memory=AgentMemory(
        db=PgMemoryDb(table_name="agent_memory", db_url=db_url),
        create_user_memories=True,
        create_session_summary=True,
    ),
    show_tool_calls=True,
    # This setting adds a tool to search the knowledge base for information
    search_knowledge=True,
    # This setting adds a tool to get chat history
    read_chat_history=True,
    # Add the previous chat history to the messages sent to the Model.
    add_history_to_messages=True,
    # This setting adds 6 previous messages from chat history to the messages sent to the LLM
    num_history_responses=6,
    markdown=True,
    debug_mode=True,
)
agent.print_response("Whats is the latest AI news?")
