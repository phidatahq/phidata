from typing import Optional

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.mistral import Mistral
from phi.embedder.mistral import MistralEmbedder
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

mistral_assistant_storage = PgAssistantStorage(
    db_url=db_url,
    # Store assistant runs in table: ai.mistral_rag_assistant
    table_name="mistral_rag_assistant",
)

mistral_assistant_knowledge = AssistantKnowledge(
    vector_db=PgVector2(
        db_url=db_url,
        # Store embeddings in table: ai.mistral_rag_documents
        collection="mistral_rag_documents",
        embedder=MistralEmbedder(),
    ),
    # 5 references are added to the prompt
    num_documents=5,
)


def get_mistral_assistant(
    model: Optional[str] = "mistral-large-latest",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Get a Mistral RAG Assistant."""

    return Assistant(
        name="mistral_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=Mistral(model=model),
        storage=mistral_assistant_storage,
        knowledge_base=mistral_assistant_knowledge,
        description="You are an AI called 'Rocket' designed to help users answer questions from your knowledge base.",
        instructions=[
            "When a user asks a question, you will be provided with information from the knowledge base.",
            "Using this information provide a clear and concise answer to the user.",
            "Keep your conversation light hearted and fun.",
        ],
        # This setting adds references from the knowledge_base to the user prompt
        add_references_to_prompt=True,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        # This setting adds chat history to the messages
        add_chat_history_to_messages=True,
        # This setting adds 4 previous messages from chat history to the messages
        num_history_messages=4,
        # This setting adds the datetime to the instructions
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
