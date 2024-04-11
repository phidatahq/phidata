from typing import Optional
from os import getenv

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm import LLM
from phi.llm.openai import OpenAIChat
from phi.llm.ollama import Hermes
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.embedder.ollama import OllamaEmbedder
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.assistant.singlestore import S2AssistantStorage
from phi.vectordb.singlestore import S2VectorDb


# -*- SingleStore Configuration -*-
USERNAME = getenv("SINGLESTORE_USERNAME")
PASSWORD = getenv("SINGLESTORE_PASSWORD")
HOST = getenv("SINGLESTORE_HOST")
PORT = getenv("SINGLESTORE_PORT")
DATABASE = getenv("SINGLESTORE_DATABASE")
SSL_CERT = getenv("SINGLESTORE_SSL_CERT")
# -*- SingleStore DB URL
db_url = f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?ssl_ca={SSL_CERT}&ssl_verify_cert=true"


def get_assistant(
    model: str = "GPT-4",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Get a Phidata Assistant with SingleStore backend."""

    # Create Assistant Storage
    assistant_storage = S2AssistantStorage(table_name="auto_rag_assistant_runs", schema=DATABASE, db_url=db_url)

    # Create default LLM and Embedder
    llm: LLM = OpenAIChat(model="gpt-4-turbo-preview")
    embedder: Embedder = OpenAIEmbedder(model="text-embedding-3-small", dimensions=1536)
    table_name = "auto_rag_documents_openai"

    if model == "Hermes2":
        llm = Hermes(model="adrienbrault/nous-hermes2pro:Q8_0")
        embedder = OllamaEmbedder(model="nomic-embed-text", dimensions=768)
        table_name = "auto_rag_documents_nomic"
    elif model == "GPT-3.5":
        llm = OpenAIChat(model="gpt-3.5-turbo-0125")

    # Create Assistant Knowledge
    assistant_knowledge = AssistantKnowledge(
        vector_db=S2VectorDb(
            collection=table_name,
            schema=DATABASE,
            db_url=db_url,
            embedder=embedder,
        ),
        num_documents=5,
    )

    return Assistant(
        name="auto_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=llm,
        storage=assistant_storage,
        knowledge_base=assistant_knowledge,
        add_chat_history_to_messages=True,
        num_history_messages=4,
        markdown=True,
        debug_mode=debug_mode,
        description="You are an AI Assistant called 'Phi' designed to help users answer questions. You have access to a knowledge base and can search the web for information if needed.",
        instructions=[
            "When a user asks a question, always search your knowledge base first using `search_knowledge_base` tool to find relevant information.",
            "If you find information relevant to the user's question, provide a clear and concise answer to the user.",
            "If you do not find information in your knowledge base, search the web using the `duckduckgo_search` tool and provide a clear and concise answer to the user.",
            "Keep your conversation light hearted and fun.",
            "Always aim to please the user",
        ],
        show_tool_calls=True,
        search_knowledge=True,
        read_chat_history=True,
        tools=[DuckDuckGo()],
    )
