from typing import Optional
from textwrap import dedent
from typing import Any, List

from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.llm import LLM
from phi.llm.groq import Groq
from phi.llm.openai import OpenAIChat
from phi.llm.ollama import OllamaTools
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.tavily import TavilyTools
from phi.tools.yfinance import YFinanceTools
from phi.vectordb.pgvector import PgVector2
from phi.embedder.openai import OpenAIEmbedder
from phi.embedder.ollama import OllamaEmbedder
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.utils.log import logger

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"


def get_llm_os_assistant(
    llm_model: str = "llama3",
    ddg_search: bool = False,
    tavily_search: bool = False,
    yfinance: bool = False,
    shell_tools: bool = False,
    file_tools: bool = False,
    python_assistant: bool = False,
    sql_assistant: bool = False,
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    num_documents: Optional[int] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Get a LLM OS."""

    logger.info(f"-*- Creating LLM OS using {llm_model} -*-")

    # Define the LLM based on the model
    llm: LLM
    if llm_model == "llama3-70b-8192":
        llm = Groq(model=llm_model)
    elif llm_model.startswith("gpt"):
        llm = OpenAIChat(model=llm_model)
    else:
        llm = OllamaTools(model=llm_model)

    # Define the knowledge base dep on the embeddings model
    knowledge_base: AssistantKnowledge
    if llm_model.startswith("gpt"):
        knowledge_base = AssistantKnowledge(
            vector_db=PgVector2(
                db_url=db_url,
                collection="llm_os_documents_openai",
                embedder=OpenAIEmbedder(model="text-embedding-3-small", dimensions=1536),
            ),
            num_documents=num_documents,
        )
    else:
        knowledge_base = AssistantKnowledge(
            vector_db=PgVector2(
                db_url=db_url,
                collection="llm_os_documents_nomic",
                embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
            ),
            num_documents=num_documents,
        )

    # Define the tools
    tools: List[Any] = []
    if ddg_search:
        tools.append(DuckDuckGo(fixed_max_results=3))
    if tavily_search:
        tools.append(TavilyTools())
    if yfinance:
        tools.append(
            YFinanceTools(stock_price=True, stock_fundamentals=True, analyst_recommendations=True, company_news=True)
        )

    llm_os_assistant = Assistant(
        name="llm_os",
        run_id=run_id,
        user_id=user_id,
        llm=llm,
        tools=tools,
        show_tool_calls=True,
        # This setting allows the LLM to search the knowledge base
        search_knowledge=True,
        # This setting allows the LLM to read chat history
        read_chat_history=True,
        # This setting adds chat history to the messages
        add_chat_history_to_messages=True,
        # This setting adds 4 previous messages from chat history to the messages sent to the LLM
        num_history_messages=4,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        # This setting adds the current datetime to the instructions
        add_datetime_to_instructions=True,
        storage=PgAssistantStorage(table_name="llm_os_assistant", db_url=db_url),
        knowledge_base=knowledge_base,
        introduction=dedent("""\
        Hi, I'm your LLM OS.\n
        Select my capabilities from the sidebar and ask me questions.
        """),
        debug_mode=debug_mode,
    )
    return llm_os_assistant
