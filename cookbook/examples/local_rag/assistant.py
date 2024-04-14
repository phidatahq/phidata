from typing import Optional

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.ollama import Ollama
from phi.embedder.ollama import OllamaEmbedder
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage

from resources import vector_db  # type: ignore

local_assistant_storage = PgAssistantStorage(
    db_url=vector_db.get_db_connection_local(),
    # Store assistant runs in table: ai.local_rag_assistant
    table_name="local_rag_assistant",
)

local_assistant_knowledge = AssistantKnowledge(
    vector_db=PgVector2(
        db_url=vector_db.get_db_connection_local(),
        # Store embeddings in table: ai.local_rag_documents
        collection="local_rag_documents",
        # Use the OllamaEmbedder to get embeddings
        embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
    ),
    # 5 references are added to the prompt
    num_documents=5,
)


def get_local_rag_assistant(
    model: str = "openhermes",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Assistant:
    """Get a Local RAG Assistant."""

    return Assistant(
        name="local_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=Ollama(model=model),
        storage=local_assistant_storage,
        knowledge_base=local_assistant_knowledge,
        # This setting adds references from the knowledge_base to the user prompt
        add_references_to_prompt=True,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        debug_mode=debug_mode,
        description="You are an AI called 'Phi' designed to help users answer questions from a knowledge base of PDFs.",
        assistant_data={"assistant_type": "rag"},
    )
