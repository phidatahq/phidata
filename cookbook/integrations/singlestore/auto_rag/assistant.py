from typing import Optional

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.ollama import Ollama
from phi.embedder.ollama import OllamaEmbedder
from phi.storage.assistant.singlestore import S2AssistantStorage
from phi.vectordb.singlestore import S2VectorDb

from resources import config  # type: ignore

# Setup SingleStore connection
db_url = (
    f"mysql+pymysql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?charset=utf8mb4"
)

local_assistant_storage = S2AssistantStorage(
    table_name="local_rag_assistant",
    schema=config["database"],
    db_url=db_url,
)

local_assistant_knowledge = AssistantKnowledge(
    vector_db=S2VectorDb(
        collection="web_documents_singlestore",
        schema=config["database"],
        db_url=db_url,
        # Assuming OllamaEmbedder or a compatible embedder is used for SingleStore
        embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
    ),
    num_documents=5,
)


def get_local_rag_assistant(
    model: str = "openhermes",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Assistant:
    """Get a Local URL RAG Assistant with SingleStore backend."""
    return Assistant(
        name="local_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=Ollama(model=model),
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
