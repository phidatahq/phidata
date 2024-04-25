from typing import Optional
from textwrap import dedent

from phi.assistant import Assistant
from phi.llm.groq import Groq
from phi.knowledge import AssistantKnowledge
from phi.embedder.ollama import OllamaEmbedder
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.utils.log import logger

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"


def get_rag_chat_assistant(
    model: str = "llama3-70b-8192",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
    num_documents: Optional[int] = None,
) -> Assistant:
    logger.info(f"-*- Creating RAG Assistant using {model} -*-")

    return Assistant(
        name="groq_rag_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=Groq(model=model),
        storage=PgAssistantStorage(table_name="groq_rag_assistant", db_url=db_url),
        knowledge_base=AssistantKnowledge(
            vector_db=PgVector2(
                db_url=db_url,
                collection="groq_rag_documents_nomic",
                embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
            ),
            num_documents=num_documents,
        ),
        description="You are an AI called 'GroqRAG' designed to assist users in the best way possible",
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
        # This setting will add the current datetime to the instructions
        add_datetime_to_instructions=True,
        # This setting adds chat history to the messages
        add_chat_history_to_messages=True,
        # Add 4 previous messages from chat history to the messages sent to the LLM
        num_history_messages=4,
        # This setting will format the messages in markdown
        markdown=True,
        debug_mode=debug_mode,
    )


def get_rag_research_assistant(
    model: str = "llama3-70b-8192",
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
    num_documents: Optional[int] = None,
) -> Assistant:
    logger.info(f"-*- Creating Research Assistant using: {model} -*-")

    return Assistant(
        name="groq_research_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=Groq(model=model),
        storage=PgAssistantStorage(table_name="groq_rag_assistant", db_url=db_url),
        knowledge_base=AssistantKnowledge(
            vector_db=PgVector2(
                db_url=db_url,
                collection="groq_research_documents_nomic",
                embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
            ),
            num_documents=num_documents,
        ),
        description="You are a Senior NYT Editor tasked with writing a NYT cover story worthy report due tomorrow.",
        instructions=[
            "You will be provided with a topic and search results from junior researchers.",
            "Carefully read the results and generate a final - NYT cover story worthy report.",
            "Make your report engaging, informative, and well-structured.",
            "Your report should follow the format provided below."
            "Remember: you are writing for the New York Times, so the quality of the report is important.",
        ],
        add_datetime_to_instructions=True,
        add_to_system_prompt=dedent("""
        <report_format>
        ## [Title]

        ### **Overview**
        Brief introduction of the report and why is it important.

        ### [Section 1]
        - **Detail 1**
        - **Detail 2**

        ### [Section 2]
        - **Detail 1**
        - **Detail 2**

        ### [Section 3]
        - **Detail 1**
        - **Detail 2**

        ## [Conclusion]
        - **Summary of report:** Recap of the key findings from the report.
        - **Implications:** What these findings mean for the future.

        ## References
        - [Reference 1](Link to Source)
        - [Reference 2](Link to Source)

        Report generated on: {Month Date, Year (hh:mm AM/PM)}
        </report_format>
        """),
        markdown=True,
        debug_mode=debug_mode,
    )
