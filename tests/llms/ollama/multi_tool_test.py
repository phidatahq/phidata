import unittest

from typing import Optional
from textwrap import dedent
from typing import Any, List

from phi.assistant import Assistant
from phi.llm.ollama import Ollama
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.yfinance import YFinanceTools


def get_function_calling_assistant(
    llm_id: str = "llama3",
    ddg_search: bool = False,
    yfinance: bool = False,
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Get a Function Calling Assistant."""

    tools: List[Any] = []
    if ddg_search:
        tools.append(DuckDuckGo(fixed_max_results=3))
    if yfinance:
        tools.append(
            YFinanceTools(
                company_info=True,
                stock_price=True,
                stock_fundamentals=True,
                analyst_recommendations=True,
                company_news=True,
            )
        )

    _llm_id = llm_id
    if llm_id == "hermes2pro-llama3":
        _llm_id = "adrienbrault/nous-hermes2pro-llama3-8b:q8_0"

    assistant = Assistant(
        name="local_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=Ollama(model=_llm_id),
        tools=tools,
        show_tool_calls=True,
        description="You can access real-time data and information by calling functions.",
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        # This setting adds the current datetime to the instructions
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
    assistant.add_introduction(
        dedent(
            """\
    Hi, I'm a local AI Assistant that uses function calling to answer questions.\n
    Select the tools from the sidebar and ask me questions.
    """
        )
    )
    return assistant


class MultiToolTestCase(unittest.TestCase):
    def test_something(self):
        local_assistant: Assistant = get_function_calling_assistant(
            llm_id="llama3.1",
            yfinance=True,
            ddg_search=False,
        )

        response: str = ""
        for delta in local_assistant.run("Whats nvidia and Tesla stock symbol and price?", stream=False):
            response += delta  # type: ignore

        self.assertNotEqual(response, "")

        response = ""
        for delta in local_assistant.run("Whats nvidia and Tesla stock symbol and price?", stream=True):
            response += delta  # type: ignore

        self.assertNotEqual(response, "")


if __name__ == "__main__":
    unittest.main()
