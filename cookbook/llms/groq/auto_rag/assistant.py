from typing import Optional

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.groq import Groq
from phi.tools.duckduckgo import DuckDuckGo
from phi.embedder.openai import OpenAIEmbedder
from phi.embedder.ollama import OllamaEmbedder
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"


def get_auto_rag_assistant(
    llm_model: str = "llama3-70b-8192",
    embeddings_model: str = "text-embedding-3-small",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Get a Groq Auto RAG Assistant."""

    # Define the embedder based on the embeddings model
    embedder = (
        OllamaEmbedder(model=embeddings_model, dimensions=768)
        if embeddings_model == "nomic-embed-text"
        else OpenAIEmbedder(model=embeddings_model, dimensions=1536)
    )
    # Define the embeddings table based on the embeddings model
    embeddings_table = (
        "auto_rag_documents_groq_ollama" if embeddings_model == "nomic-embed-text" else "auto_rag_documents_groq_openai"
    )

    return Assistant(
        name="auto_rag_assistant_groq",
        run_id=run_id,
        user_id=user_id,
        llm=Groq(model=llm_model),
        storage=PgAssistantStorage(table_name="auto_rag_assistant_groq", db_url=db_url),
        knowledge_base=AssistantKnowledge(
            vector_db=PgVector2(
                db_url=db_url,
                collection=embeddings_table,
                embedder=embedder,
            ),
            # 3 references are added to the prompt
            num_documents=3,
        ),
        description="You are an Assistant called 'AutoRAG' that answers questions by calling functions.",
        instructions=[
            "First get additional information about the users question.",
            "You can either use the `search_knowledge_base` tool to search your knowledge base or the `duckduckgo_search` tool to search the internet.",
            "If the user asks about current events, use the `duckduckgo_search` tool to search the internet.",
            "If the user asks to summarize the conversation, use the `get_chat_history` tool to get your chat history with the user.",
            "Carefully process the information you have gathered and provide a clear and concise answer to the user.",
            "Respond directly to the user with your answer, do not say 'here is the answer' or 'this is the answer' or 'According to the information provided'",
            "NEVER mention your knowledge base or say 'According to the search_knowledge_base tool' or 'According to {some_tool} tool'.",
        ],
        # Show tool calls in the chat
        show_tool_calls=True,
        # This setting gives the LLM a tool to search for information
        search_knowledge=True,
        # This setting gives the LLM a tool to get chat history
        read_chat_history=True,
        tools=[DuckDuckGo()],
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        # Adds chat history to messages
        add_chat_history_to_messages=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
