from typing import Optional
from os import getenv

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.openai import OpenAIChat
from phi.llm.anthropic import Claude
from phi.llm.ollama import Hermes
from phi.embedder.ollama import OllamaEmbedder
from phi.storage.assistant.singlestore import S2AssistantStorage
from phi.vectordb.singlestore import S2VectorDb


# Setup SingleStore connection
db_url = f"mysql+pymysql://{getenv("SINGLESTORE_USERNAME")}:{getenv("SINGLESTORE_PASSWORD")}@{getenv("SINGLESTORE_HOST")}:{getenv("SINGLESTORE_PORT")}/{getenv("SINGLESTORE_DATABASE")}?ssl_ca={getenv("SINGLESTORE_SSL_CERT")}&ssl_verify_cert=true"

local_assistant_storage = S2AssistantStorage(
    table_name="local_rag_assistant",
    schema=getenv("SINGLESTORE_DATABASE"),
    db_url=db_url,
)

local_assistant_knowledge = AssistantKnowledge(
    vector_db=S2VectorDb(
        collection="web_documents_singlestore",
        schema=getenv("SINGLESTORE_DATABASE"),
        db_url=db_url,
        # Assuming OllamaEmbedder or a compatible embedder is used for SingleStore
        embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
    ),
    num_documents=5,
)


def get_local_rag_assistant(
    model: str = "GPT-4",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Assistant:
    """Get a Local URL RAG Assistant with SingleStore backend."""

    if model == "GPT-4":
        llm = OpenAIChat(model="gpt-4-turbo-preview")
    elif model == "Hermes2":
        llm = Hermes(model="adrienbrault/nous-hermes2pro:Q8_0")
    elif model == "Claude":
        llm = Claude(model="claude-3-opus-20240229")

    return Assistant(
        name="local_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=llm,
        storage=local_assistant_storage,
        knowledge_base=local_assistant_knowledge,
        add_chat_history_to_messages=False,
        add_references_to_prompt=True,
        num_history_messages=4,
        markdown=True,
        debug_mode=debug_mode,
        description="You are an AI called 'Phi' designed to help users answer questions from a knowledge base.",
        assistant_data={"assistant_type": "rag"},
        use_tools=True,
        show_tool_calls=True,
    )
