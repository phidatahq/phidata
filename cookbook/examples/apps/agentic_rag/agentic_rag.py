"""🏎️ Agentic RAG Agent - Your AI Data Analyst!

This advanced example shows how to build a Agentic RAG Agent that
leverages Agentic RAG to provide deep insights into any data.

Example queries to try:
- "summarize the document"
- "what is the key insights"
- "what are the important statistics"


View the README for instructions on how to run the application.
"""

from typing import Optional
import os
from agno.agent import Agent, AgentMemory
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.embedder.openai import OpenAIEmbedder
from agno.vectordb.qdrant import Qdrant
from agno.knowledge import AgentKnowledge
from agno.memory.db.postgres import PgMemoryDb
from agno.storage.agent.postgres import PostgresAgentStorage
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"


def get_auto_rag_agent(
    model_id: str = "gpt-4o-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Get an Auto RAG Agent with Memory."""

    # Define persistent memory for chat history
    memory = AgentMemory(
        db=PgMemoryDb(table_name="agent_memory", db_url=db_url),  # Persist memory in Postgres
        create_user_memories=True,  # Store user preferences
        create_session_summary=True,  # Store conversation summaries
    )

    # Define the knowledge base
    knowledge_base = AgentKnowledge(
        vector_db=Qdrant(
            collection="auto_rag_documents_openai",
            embedder=OpenAIEmbedder(id="text-embedding-ada-002", dimensions=1536),
        ),
        num_documents=3,  # Retrieve 3 most relevant documents
    )

    # Create the Agent
    auto_rag_agent: Agent = Agent(
        name="auto_rag_agent",
        session_id=session_id,  # Track session ID for persistent conversations
        user_id=user_id,
        model=OpenAIChat(id=model_id),
        storage=PostgresAgentStorage(table_name="auto_rag_agent_sessions", db_url=db_url),  # Persist session data
        memory=memory,  # Add memory to the agent
        knowledge=knowledge_base,  # Add knowledge base
        description="You are a helpful Agent called 'AutoRAG' and your goal is to assist the user in the best way possible.",
        instructions=[
            "Given a user query, first ALWAYS search your knowledge base using the search_knowledge_base tool to see if you have relevant information.",
            "If you don't find relevant information in your knowledge base, use the duckduckgo_search tool to search the internet.",
            "If you need to reference the chat history, use the get_chat_history tool.",
            "If the user's question is unclear, ask clarifying questions to get more information.",
            "Carefully read the information you have gathered and provide a clear and concise answer to the user.",
            "Do not use phrases like 'based on my knowledge' or 'depending on the information'.",
        ],
        search_knowledge=True,  # This setting gives the model a tool to search the knowledge base for information
        read_chat_history=True,  # This setting gives the model a tool to get chat history
        tools=[DuckDuckGoTools()],
        markdown=True,  # This setting tellss the model to format messages in markdown
        # add_chat_history_to_messages=True,
        show_tool_calls=True,
        add_history_to_messages=True,  # Adds chat history to messages
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
        read_tool_call_history=True,
        num_history_responses=3,
    )

    return auto_rag_agent
