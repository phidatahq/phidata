from typing import Optional
from textwrap import dedent
from typing import Any, List

from phi.assistant import Assistant
from phi.llm.ollama import OllamaTools
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.tavily import TavilyTools
from phi.tools.yfinance import YFinanceTools


def get_local_assistant(
    llm_model: str = "llama3",
    ddg_search: bool = False,
    tavily_search: bool = False,
    yfinance: bool = False,
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Get a Local Autonomous Assistant."""

    tools: List[Any] = []
    if ddg_search:
        tools.append(DuckDuckGo(fixed_max_results=3))
    if tavily_search:
        tools.append(TavilyTools())
    if yfinance:
        tools.append(
            YFinanceTools(stock_price=True, stock_fundamentals=True, analyst_recommendations=True, company_news=True)
        )

    assistant = Assistant(
        name="local_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=OllamaTools(model=llm_model),
        tools=tools,
        show_tool_calls=True,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
    assistant.add_introduction(
        dedent("""\
    Hi, I'm a local AI Assistant that uses function calling to answer questions.\n
    Select the tools from the sidebar and ask me questions.
    """)
    )
    return assistant
