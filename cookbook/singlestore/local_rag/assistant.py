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
    f"mysql+pymysql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
)

local_assistant_storage = S2AssistantStorage(
    table_name="local_rag_assistant",
    schema=config["database"],
    db_url=db_url,
)

local_assistant_knowledge = AssistantKnowledge(
    vector_db=S2VectorDb(
        collection="local_rag_documents",
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
    """Get a Local RAG Assistant with SingleStore backend."""

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
        use_tools=True,
        show_tool_calls=True,
    )
