from typing import Optional

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.ollama import Ollama
from phi.embedder.ollama import OllamaEmbedder
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"


def get_rag_assistant(
    model: str = "llama3",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Get a Local RAG Assistant."""

    knowledge = AssistantKnowledge(
        vector_db=PgVector2(
            db_url=db_url,
            # Store embeddings in table: ai.local_rag_documents
            collection=f"local_rag_documents_{model}",
            embedder=OllamaEmbedder(model=model, dimensions=4096),
        ),
        # 2 references are added to the prompt
        num_documents=2,
    )

    return Assistant(
        name="local_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=Ollama(model=model),
        storage=PgAssistantStorage(table_name="local_rag_assistant", db_url=db_url),
        knowledge_base=knowledge,
        # This setting adds references from the knowledge_base to the user prompt
        add_references_to_prompt=True,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        debug_mode=debug_mode,
        description="You are an AI called 'RAGit' and your task is to answer questions from a knowledge base",
        instructions=[
            "When a user asks a question, you will be provided with information from a knowledge base.",
            "Using this information provide a clear and concise answer to the user.",
            "Do not use phrases like 'based on my knowledge' or 'depending on the article'.",
        ],
        add_datetime_to_instructions=True,
    )
