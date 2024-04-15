from typing import Optional
from os import getenv

from sqlalchemy.engine import create_engine

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm.openai import OpenAIChat
from phi.llm.ollama import Ollama
from phi.embedder.openai import OpenAIEmbedder
from phi.embedder.ollama import OllamaEmbedder
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.assistant.singlestore import S2AssistantStorage  # noqa
from phi.vectordb.singlestore import S2VectorDb
from phi.utils.log import logger

# -*- SingleStore Configuration -*-
USERNAME = getenv("SINGLESTORE_USERNAME")
PASSWORD = getenv("SINGLESTORE_PASSWORD")
HOST = getenv("SINGLESTORE_HOST")
PORT = getenv("SINGLESTORE_PORT")
DATABASE = getenv("SINGLESTORE_DATABASE")
SSL_CERT = getenv("SINGLESTORE_SSL_CERT", None)
# -*- SingleStore DB URL
db_url = f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?charset=utf8mb4"
if SSL_CERT:
    db_url += f"&ssl_ca={SSL_CERT}&ssl_verify_cert=true"
# -*- SingleStore DB Engine
db_engine = create_engine(db_url)


def get_assistant(
    model: str = "GPT-4",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
    web_search: bool = False,
) -> Assistant:
    """Get a Phidata Assistant with SingleStore backend."""

    logger.info(f"Creating Assistant. Model: {model} | Run ID: {run_id}")
    logger.info(f"SingleStore DB: {db_url}")

    if model == "Hermes2":
        return Assistant(
            name="auto_rag_assistant_hermes2",
            run_id=run_id,
            user_id=user_id,
            llm=Ollama(model="adrienbrault/nous-hermes2pro:Q8_0"),
            # storage=S2AssistantStorage(table_name="auto_rag_assistant_hermes2", schema=DATABASE, db_engine=db_engine),
            knowledge_base=AssistantKnowledge(
                vector_db=S2VectorDb(
                    collection="auto_rag_documents_nomic",
                    schema=DATABASE,
                    db_engine=db_engine,
                    embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
                ),
                num_documents=2,
            ),
            markdown=True,
            debug_mode=debug_mode,
            description="You are an AI Assistant called 'Phi' designed to help users answer questions about SingleStore.",
            instructions=[
                "When a user asks a question, you will be provided with information from the knowledge base.",
                "Using this information provide a clear and concise answer to the user.",
                "Share links where possible and use bullet points to make information easier to read.",
                "Keep your conversation light hearted and fun.",
                "Do not use emojis or slang in your responses.",
            ],
            # This setting will add the references from the vector store to the prompt
            add_references_to_prompt=True,
        )
    else:
        model_name = "gpt-4-turbo" if model == "GPT-4" else "gpt-3.5-turbo-0125"
        instructions = [
            "When a user asks a question, always search your knowledge base using `search_knowledge_base` tool to find relevant information.",
            "If you find information relevant to the user's question, provide a clear and concise answer to the user.",
        ]
        if web_search:
            instructions.extend(
                [
                    "If you do not find information in your knowledge base, search the web using the `duckduckgo_search` tool and provide a clear and concise answer to the user.",
                ]
            )
        instructions.extend(
            [
                "Share links where possible and use bullet points to make information easier to read.",
                "Keep your conversation light hearted and fun.",
                "Always aim to please the user",
                "Do not use emojis or slang in your responses.",
            ]
        )

        return Assistant(
            name="auto_rag_assistant_openai",
            run_id=run_id,
            user_id=user_id,
            llm=OpenAIChat(model=model_name),
            # storage=S2AssistantStorage(table_name="auto_rag_assistant_openai", schema=DATABASE, db_engine=db_engine),
            knowledge_base=AssistantKnowledge(
                vector_db=S2VectorDb(
                    collection="auto_rag_documents_openai",
                    schema=DATABASE,
                    db_engine=db_engine,
                    embedder=OpenAIEmbedder(model="text-embedding-3-small", dimensions=1536),
                ),
                num_documents=5,
            ),
            # This setting adds chat history to the messages
            add_chat_history_to_messages=True,
            num_history_messages=4,
            markdown=True,
            debug_mode=debug_mode,
            description="You are an AI Assistant called 'Phi' designed to help users answer questions about SingleStore.",
            instructions=instructions,
            show_tool_calls=True,
            search_knowledge=True,
            read_chat_history=True,
            tools=[DuckDuckGo()] if web_search else [],
        )
