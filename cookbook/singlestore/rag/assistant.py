from os import getenv
from typing import Optional

from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.knowledge import AssistantKnowledge
from phi.storage.assistant.singlestore import S2AssistantStorage
from phi.vectordb.singlestore import S2VectorDb

from resources import config  # type: ignore

host = getenv("SINGLESTORE_HOST", config["host"])
port = getenv("SINGLESTORE_PORT", config["port"])
username = getenv("SINGLESTORE_USERNAME", config["username"])
password = getenv("SINGLESTORE_PASSWORD", config["password"])
database = getenv("SINGLESTORE_DATABASE", config["database"])
ssl_ca = getenv("SINGLESTORE_SSL_CA", config["ssl_ca"])

db_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?ssl_ca={ssl_ca}&ssl_verify_cert=true"

assistant_storage = S2AssistantStorage(table_name="pdf_assistant", schema=database, db_url=db_url)

assistant_knowledge = AssistantKnowledge(
    vector_db=S2VectorDb(collection="pdf_documents", schema=database, db_url=db_url),
    num_documents=5,
)


def get_pdf_assistant(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Assistant:
    return Assistant(
        name="pdf_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=OpenAIChat(model="gpt-4-turbo-preview"),
        storage=assistant_storage,
        knowledge_base=assistant_knowledge,
        use_tools=True,
        show_tool_calls=True,
        # This setting adds the last 4 messages from the chat history to the API call
        add_chat_history_to_messages=True,
        num_history_messages=4,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        debug_mode=debug_mode,
        description="You are 'SingleStoreAI' designed to help users answer questions from a knowledge base of PDFs.",
    )
