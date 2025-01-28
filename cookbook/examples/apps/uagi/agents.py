"""🤖 Universal Agent Interface (UAgI) - Your AI Operating System!

This advanced example demonstrates how to build a sophisticated AI operating system that coordinates
multiple AI agents, tools, and capabilities - similar to how an operating system manages computer resources.

Core capabilities:
- Multi-agent coordination (Research, Investment, Python agents)
- Multi-modal interactions (text, data, code)
- Persistent knowledge and memory
- Tool integration (calculator, file system, web search)
- Reasoning and delegation

Example queries to try:
Simple tasks:
- "What's in my knowledge base about GPT-4?"
- "Calculate the compound interest on $1000 over 5 years at 8% APR"
- "What files are in the current directory?"
- "Search the latest news about AI regulation"

Research tasks:
- "Write a detailed report about quantum computing advances in 2024"
- "Research the impact of AI on healthcare and create a summary"
- "Analyze the current state of autonomous vehicles"

Investment analysis:
- "Analyze NVIDIA's stock performance and future prospects"
- "Compare Tesla vs other EV makers' stock performance"
- "Give me an investment report on Microsoft"

Programming tasks:
- "Write a Python script to analyze CSV data"
- "Help debug this error in my code"
- "Create a simple web scraper in Python"

Multi-agent collaboration:
- "Research quantum computing and write a Python script to simulate a quantum gate"
- "Analyze Tesla's financials and create a visualization using Python"
- "Research AI regulation and prepare a report with data analysis"

View the README for detailed setup instructions and additional examples.
"""

import os
from pathlib import Path
from textwrap import dedent
from typing import List, Optional

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.combined import CombinedKnowledgeBase
from agno.knowledge.json import JSONKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.models.anthropic import Claude
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools import Toolkit
from agno.tools.calculator import CalculatorTools
from agno.tools.duckdb import DuckDbTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.exa import ExaTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.tools.yfinance import YFinanceTools
from agno.utils.log import logger
from agno.vectordb.pgvector import PgVector

# ************* Database Connection *************
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
# *******************************

# ************* Paths *************
cwd = Path(__file__).parent.resolve()
knowledge_dir = cwd.joinpath("knowledge")
output_dir = cwd.joinpath("output")

# Create the output directory if it does not exist
output_dir.mkdir(parents=True, exist_ok=True)
# *******************************

# ************* Storage & Knowledge *************
agent_storage = PostgresAgentStorage(
    db_url=db_url,
    # Store agent sessions in the ai.uagi_sessions table
    table_name="uagi_sessions",
    schema="ai",
)
agent_knowledge = CombinedKnowledgeBase(
    sources=[
        # Reads text files, SQL files, and markdown files
        TextKnowledgeBase(
            path=knowledge_dir,
            formats=[".txt", ".sql", ".md"],
        ),
        # Reads JSON files
        JSONKnowledgeBase(path=knowledge_dir),
    ],
    # Store agent knowledge in the ai.uagi_knowledge table
    vector_db=PgVector(
        db_url=db_url,
        table_name="uagi_knowledge",
        schema="ai",
        # Use OpenAI embeddings
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
    # 5 references are added to the prompt
    num_documents=5,
)
# *******************************


def get_uagi(
    user_id: Optional[str] = None,
    model_id: str = "openai:gpt-4o",
    session_id: Optional[str] = None,
    calculator: bool = False,
    ddg_search: bool = False,
    exa_search: bool = False,
    firecrawl_scraping: bool = False,
    file_tools: bool = False,
    shell_tools: bool = False,
    data_analyst: bool = False,
    python_agent: bool = False,
    research_agent: bool = False,
    investment_agent: bool = False,
    debug_mode: bool = True,
) -> Agent:
    """Returns an instance of the Universal Agent Interface (UAgI).

    Args:
        user_id: Optional user identifier
        model_id: Model identifier in format 'provider:model_name'
        session_id: Optional session identifier
        calculator: Enable calculator tools
        ddg_search: Enable DuckDuckGo search
        exa_search: Enable Exa search
        firecrawl_scraping: Enable Firecrawl web scraping
        file_tools: Enable file system operations
        shell_tools: Enable shell commands
        data_analyst: Enable Data Analyst agent
        python_agent: Enable Python Programming agent
        research_agent: Enable Research Report agent
        investment_agent: Enable Investment Analysis agent
        debug_mode: Enable debug logging
    """
    logger.info(f"-*- Creating UAgI using {model_id} -*-")

    tools: List[Toolkit] = []
    extra_instructions: List[str] = []

    if calculator:
        # enables addition, subtraction, multiplication, division, check prime, exponential, factorial, square root
        tools.append(CalculatorTools(enable_all=True))
    if ddg_search:
        tools.append(DuckDuckGoTools())
    if shell_tools:
        tools.append(ShellTools())
        extra_instructions.append(
            "You can use the `run_shell_command` tool to run shell commands. For example, `run_shell_command(args='ls')`."
        )
    if file_tools:
        tools.append(FileTools(base_dir=cwd))
        extra_instructions.append(
            "You can use the `read_file` tool to read a file, `save_file` to save a file, and `list_files` to list files in the working directory."
        )

    # Add team members available to the UAgI
    team: List[Agent] = []
    if data_analyst:
        _data_analyst: Agent = Agent(
            tools=[DuckDbTools()],
            show_tool_calls=True,
            instructions="Use this file for Movies data: https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
        )
        team.append(_data_analyst)
        extra_instructions.append(
            "To answer questions about my favorite movies, delegate the task to the `Data Analyst`."
        )

    if python_agent:
        _python_agent: Agent = Agent(
            tools=[PythonTools(base_dir=Path("tmp/python"))],
            show_tool_calls=True,
            instructions="To write and run Python code, delegate the task to the `Python Agent`.",
        )

        team.append(_python_agent)
        extra_instructions.append(
            "To write and run Python code, delegate the task to the `Python Agent`."
        )
    if research_agent:
        _research_agent = Agent(
            name="Research Agent",
            role="Write a research report on a given topic",
            model=OpenAIChat(id=model_id),
            description="You are a Senior New York Times researcher tasked with writing a cover story research report.",
            instructions=[
                "For a given topic, use the `search_exa` to get the top 10 search results.",
                "Carefully read the results and generate a final - NYT cover story worthy report in the <report_format> provided below.",
                "Make your report engaging, informative, and well-structured.",
                "Remember: you are writing for the New York Times, so the quality of the report is important.",
            ],
            expected_output=dedent(
                """\
            An engaging, informative, and well-structured report in the following format:
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

            ## Conclusion
            - **Summary of report:** Recap of the key findings from the report.
            - **Implications:** What these findings mean for the future.

            ## References
            - [Reference 1](Link to Source)
            - [Reference 2](Link to Source)
            </report_format>
            """
            ),
            tools=[ExaTools(num_results=3, text_length_limit=1000)],
            markdown=True,
            debug_mode=debug_mode,
        )
        team.append(_research_agent)
        extra_instructions.append(
            "To write a research report, delegate the task to the `Research Agent`. "
            "Return the report in the <report_format> to the user as is, without any additional text like 'here is the report'."
        )

    if investment_agent:
        _investment_agent = Agent(
            name="Investment Agent",
            role="Write an investment report on a given company (stock) symbol",
            model=OpenAIChat(id=model_id),
            description="You are a Senior Investment Analyst for Goldman Sachs tasked with writing an investment report for a very important client.",
            instructions=[
                "For a given stock symbol, get the stock price, company information, analyst recommendations, and company news",
                "Carefully read the research and generate a final - Goldman Sachs worthy investment report in the <report_format> provided below.",
                "Provide thoughtful insights and recommendations based on the research.",
                "When you share numbers, make sure to include the units (e.g., millions/billions) and currency.",
                "REMEMBER: This report is for a very important client, so the quality of the report is important.",
            ],
            expected_output=dedent(
                """\
            <report_format>
            ## [Company Name]: Investment Report

            ### **Overview**
            {give a brief introduction of the company and why the user should read this report}
            {make this section engaging and create a hook for the reader}

            ### Core Metrics
            {provide a summary of core metrics and show the latest data}
            - Current price: {current price}
            - 52-week high: {52-week high}
            - 52-week low: {52-week low}
            - Market Cap: {Market Cap} in billions
            - P/E Ratio: {P/E Ratio}
            - Earnings per Share: {EPS}
            - 50-day average: {50-day average}
            - 200-day average: {200-day average}
            - Analyst Recommendations: {buy, hold, sell} (number of analysts)

            ### Financial Performance
            {analyze the company's financial performance}

            ### Growth Prospects
            {analyze the company's growth prospects and future potential}

            ### News and Updates
            {summarize relevant news that can impact the stock price}

            ### [Summary]
            {give a summary of the report and what are the key takeaways}

            ### [Recommendation]
            {provide a recommendation on the stock along with a thorough reasoning}

            </report_format>
            """
            ),
            tools=[
                YFinanceTools(
                    stock_price=True,
                    company_info=True,
                    analyst_recommendations=True,
                    company_news=True,
                )
            ],
            markdown=True,
            debug_mode=debug_mode,
            add_datetime_to_instructions=True,
        )
        team.append(_investment_agent)
        extra_instructions.extend(
            [
                "To get an investment report on a stock, delegate the task to the `Investment Agent`. "
                "Return the report in the <report_format> to the user without any additional text like 'here is the report'.",
                "Answer any questions they may have using the information in the report.",
                "Never provide investment advise without the investment report.",
            ]
        )

    # Parse model provider and name
    provider, model_name = model_id.split(":")

    # Select appropriate model class based on provider
    if provider == "openai":
        model = OpenAIChat(id=model_name)
    elif provider == "google":
        model = Gemini(id=model_name)
    elif provider == "anthropic":
        model = Claude(id=model_name)
    else:
        raise ValueError(f"Unsupported model provider: {provider}")

    # Create the UAgI
    uagi = Agent(
        name="uagi",
        model=model,
        user_id=user_id,
        session_id=session_id,
        storage=agent_storage,
        knowledge=agent_knowledge,
        # Enable Agentic RAG i.e. the ability to search the knowledge base on-demand
        search_knowledge=True,
        # Enable the ability to read the chat history
        read_chat_history=True,
        # Enable the ability to read the tool call history
        read_tool_call_history=True,
        # Add tools to the agent
        tools=tools,
        team=team,
        add_history_to_messages=True,
        num_history_responses=3,
        description=dedent("""\
        I am UAgI (Universal Agent Interface), an advanced AI operating system inspired by the concept that LLMs can serve as the kernel of an AI-powered OS.

        My core capabilities include:
        🧠 Coordinating multiple specialized AI agents
        🔧 Managing various tools and system resources
        💾 Maintaining persistent knowledge and memory
        🤝 Facilitating multi-modal interactions
        🎯 Problem-solving through reasoning and delegation

        Think of me as your AI command center - I can help you with:
        - Research and analysis
        - Investment insights
        - Programming and debugging
        - Data analysis
        - System operations
        - Web search and information retrieval"""),
        instructions=dedent("""\
        As an AI Operating System, follow these core protocols:

        1. RESOURCE MANAGEMENT
        - Efficiently coordinate between available agents and tools
        - Maintain context across interactions
        - Manage knowledge base access and updates

        2. TASK PROCESSING
        - Analyze incoming requests for required capabilities
        - Break complex tasks into manageable sub-tasks
        - Delegate to specialized agents when appropriate
        - Monitor and coordinate multi-step processes

        3. KNOWLEDGE UTILIZATION
        - Always check knowledge base first using `search_knowledge_base`
        - Reference relevant past interactions
        - Update knowledge base with new insights

        4. INTERACTION PROTOCOLS
        - Maintain clear communication about actions and reasoning
        - Ask for clarification when needed
        - Provide progress updates on complex tasks
        - Format responses appropriately (markdown, tables, etc.)

        5. SECURITY AND VALIDATION
        - Verify information accuracy
        - Never make assumptions without checking
        - Protect system resources
        - Follow tool-specific security protocols

        6. ERROR HANDLING
        - Gracefully handle failures
        - Provide clear error messages
        - Suggest alternative approaches when needed
        - Learn from unsuccessful attempts

        CRITICAL RULES:
        - Never execute destructive commands
        - Always verify before critical operations
        - Maintain user privacy and security
        - Document important decisions and actions
        - Stay within authorized capabilities"""),
        markdown=True,
        debug_mode=debug_mode,
    )

    return uagi
