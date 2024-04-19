from typing import Optional

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.groq import Groq
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"


def get_groq_assistant(
    model: str = "llama3",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Get a Local RAG Assistant."""

    return Assistant(
        name="groq_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=Groq(model=model),
        storage=PgAssistantStorage(table_name="groq_rag_assistant", db_url=db_url),
        knowledge_base=AssistantKnowledge(
            vector_db=PgVector2(
                db_url=db_url,
                collection="groq_rag_documents",
                embedder=OpenAIEmbedder(model="text-embedding-3-small"),
            ),
            # 2 references are added to the prompt
            num_documents=2,
        ),
        description="You are an AI called 'GroqRAG' and your task is to answer questions from a knowledge base",
        instructions=[
            "When a user asks a question, you will be provided with information from the knowledge base.",
            "Using this information provide a clear and concise answer to the user.",
            "Do not use phrases like 'based on my knowledge' or 'depending on the article'.",
        ],
        # This setting adds references from the knowledge_base to the user prompt
        add_references_to_prompt=True,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        # This setting adds chat history to the messages
        add_chat_history_to_messages=True,
        # This setting adds 4 previous messages from chat history to the messages
        num_history_messages=4,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
