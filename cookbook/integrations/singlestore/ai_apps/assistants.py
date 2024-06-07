from os import getenv
from typing import Optional
from textwrap import dedent

from sqlalchemy.engine import create_engine

from phi.assistant import Assistant
from phi.llm import LLM
from phi.llm.groq import Groq
from phi.llm.ollama import Ollama
from phi.llm.openai import OpenAIChat
from phi.knowledge import AssistantKnowledge
from phi.embedder.openai import OpenAIEmbedder
from phi.embedder.ollama import OllamaEmbedder
from phi.storage.assistant.singlestore import S2AssistantStorage  # noqa
from phi.vectordb.singlestore import S2VectorDb
from phi.utils.log import logger

# ************** Create SingleStore Database Engine **************
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
# -*- single_store_db_engine
db_engine = create_engine(db_url)
# ****************************************************************


def get_rag_assistant(
    llm_model: str = "gpt-4-turbo",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
    num_documents: Optional[int] = None,
) -> Assistant:
    """Get a RAG Assistant with SingleStore backend."""

    logger.info(f"-*- Creating RAG Assistant. LLM: {llm_model} -*-")

    if llm_model.startswith("gpt"):
        return Assistant(
            name="singlestore_rag_assistant",
            run_id=run_id,
            user_id=user_id,
            llm=OpenAIChat(model=llm_model),
            knowledge_base=AssistantKnowledge(
                vector_db=S2VectorDb(
                    collection="rag_documents_openai",
                    schema=DATABASE,
                    db_engine=db_engine,
                    embedder=OpenAIEmbedder(model="text-embedding-3-small", dimensions=1536),
                ),
                num_documents=num_documents,
            ),
            description="You are an AI called 'SQrL' designed to assist users in the best way possible",
            instructions=[
                "When a user asks a question, first search your knowledge base using `search_knowledge_base` tool to find relevant information.",
                "Carefully read relevant information and provide a clear and concise answer to the user.",
                "You must answer only from the information in the knowledge base.",
                "Share links where possible and use bullet points to make information easier to read.",
                "Do not use phrases like 'based on my knowledge' or 'depending on the information'.",
                "Keep your conversation light hearted and fun.",
                "Always aim to please the user",
            ],
            show_tool_calls=True,
            search_knowledge=True,
            read_chat_history=True,
            # This setting adds chat history to the messages list
            add_chat_history_to_messages=True,
            # Add 6 messages from the chat history to the messages list
            num_history_messages=6,
            add_datetime_to_instructions=True,
            # -*- Disable storage in the start
            # storage=S2AssistantStorage(table_name="auto_rag_assistant_openai", schema=DATABASE, db_engine=db_engine),
            markdown=True,
            debug_mode=debug_mode,
        )
    else:
        llm: LLM = Ollama(model=llm_model)
        if llm_model == "llama3-70b-8192":
            llm = Groq(model=llm_model)

        return Assistant(
            name="singlestore_rag_assistant",
            run_id=run_id,
            user_id=user_id,
            llm=llm,
            knowledge_base=AssistantKnowledge(
                vector_db=S2VectorDb(
                    collection="rag_documents_nomic",
                    schema=DATABASE,
                    db_engine=db_engine,
                    embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
                ),
                num_documents=num_documents,
            ),
            description="You are an AI called 'SQrL' designed to assist users in the best way possible",
            instructions=[
                "When a user asks a question, you will be provided with relevant information to answer the question.",
                "Carefully read relevant information and provide a clear and concise answer to the user.",
                "You must answer only from the information in the knowledge base.",
                "Share links where possible and use bullet points to make information easier to read.",
                "Keep your conversation light hearted and fun.",
                "Always aim to please the user",
            ],
            # This setting will add the references from the vector store to the prompt
            add_references_to_prompt=True,
            add_datetime_to_instructions=True,
            markdown=True,
            debug_mode=debug_mode,
            # -*- Disable memory to save on tokens
            # This setting adds chat history to the messages
            # add_chat_history_to_messages=True,
            # num_history_messages=4,
            # -*- Disable storage in the start
            # storage=S2AssistantStorage(table_name="auto_rag_assistant_ollama", schema=DATABASE, db_engine=db_engine),
        )


def get_research_assistant(
    llm_model: str = "gpt-4-turbo",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
    num_documents: Optional[int] = None,
) -> Assistant:
    """Get a Research Assistant with SingleStore backend."""

    logger.info(f"-*- Creating Research Assistant. LLM: {llm_model} -*-")

    llm: LLM = Ollama(model=llm_model)
    if llm_model == "llama3-70b-8192":
        llm = Groq(model=llm_model)

    knowledge_base = AssistantKnowledge(
        vector_db=S2VectorDb(
            collection="research_documents_nomic",
            schema=DATABASE,
            db_engine=db_engine,
            embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
        ),
        num_documents=num_documents,
    )

    if llm_model.startswith("gpt"):
        llm = OpenAIChat(model=llm_model)
        knowledge_base = AssistantKnowledge(
            vector_db=S2VectorDb(
                collection="research_documents_openai",
                schema=DATABASE,
                db_engine=db_engine,
                embedder=OpenAIEmbedder(model="text-embedding-3-small", dimensions=1536),
            ),
            num_documents=num_documents,
        )

    return Assistant(
        name="singlestore_research_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=llm,
        knowledge_base=knowledge_base,
        description="You are a Senior NYT Editor tasked with writing a NYT cover story worthy report due tomorrow.",
        instructions=[
            "You will be provided with a topic and search results from junior researchers.",
            "Carefully read the results and generate a final - NYT cover story worthy report.",
            "Make your report engaging, informative, and well-structured.",
            "Your report should follow the format provided below."
            "Remember: you are writing for the New York Times, so the quality of the report is important.",
        ],
        add_datetime_to_instructions=True,
        add_to_system_prompt=dedent(
            """
        <report_format>
        ## Title

        - **Overview** Brief introduction of the topic.
        - **Importance** Why is this topic significant now?

        ### Section 1
        - **Detail 1**
        - **Detail 2**

        ### Section 2
        - **Detail 1**
        - **Detail 2**

        ### Section 3
        - **Detail 1**
        - **Detail 2**

        ## Conclusion
        - **Summary of report:** Recap of the key findings from the report.
        - **Implications:** What these findings mean for the future.

        ## References
        - [Reference 1](Link to Source)
        - [Reference 2](Link to Source)
        - Report generated on: {Month Date, Year (hh:mm AM/PM)}
        </report_format>
        """
        ),
        markdown=True,
        debug_mode=debug_mode,
        # -*- Disable memory to save on tokens
        # This setting adds chat history to the messages
        # add_chat_history_to_messages=True,
        # num_history_messages=4,
        # -*- Disable storage in the start
        # storage=S2AssistantStorage(table_name="auto_rag_assistant_ollama", schema=DATABASE, db_engine=db_engine),
    )
