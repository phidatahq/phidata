from typing import Optional

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.groq import Groq
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage

from resources import vector_db  # type: ignore

groq_assistant_storage = PgAssistantStorage(
    db_url=vector_db.get_db_connection_local(),
    # Store assistant runs in table: ai.groq_rag_assistant
    table_name="groq_rag_assistant",
)

groq_assistant_knowledge = AssistantKnowledge(
    vector_db=PgVector2(
        db_url=vector_db.get_db_connection_local(),
        # Store embeddings in table: ai.groq_rag_documents
        collection="groq_rag_documents",
        embedder=OpenAIEmbedder(model="text-embedding-3-small"),
    ),
    # 5 references are added to the prompt
    num_documents=5,
)


def get_groq_assistant(
    model: str = "groq-large-latest",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Assistant:
    """Get a Mistral RAG Assistant."""

    return Assistant(
        name="mixtral-8x7b-32768",
        run_id=run_id,
        user_id=user_id,
        llm=Groq(model=model),
        storage=groq_assistant_storage,
        knowledge_base=groq_assistant_knowledge,
        # This setting adds references from the knowledge_base to the user prompt
        add_references_to_prompt=True,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        # This setting adds chat history to the messages
        add_chat_history_to_messages=True,
        # This setting adds 4 previous messages from chat history to the messages
        num_history_messages=4,
        debug_mode=debug_mode,
        description="You are an AI called 'Phi' designed to help users answer questions from a knowledge base of PDFs.",
    )
