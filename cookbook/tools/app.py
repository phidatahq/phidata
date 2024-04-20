from textwrap import dedent
from typing import Any, List

import streamlit as st
from phi.assistant import Assistant
from phi.tools.exa import ExaTools
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.yfinance import YFinanceTools
from phi.utils.log import logger

st.set_page_config(
    page_title="Tool Calling Demo",
    page_icon=":orange_heart:",
)
st.title("Tool Calling Demo")
st.markdown("##### :orange_heart: built with [phidata](https://github.com/phidatahq/phidata)")


def clear_assistant():
    st.session_state["assistant"] = None


def create_assistant(
    web_search: bool = False, exa_search: bool = False, yfinance: bool = False, debug_mode: bool = False
) -> Assistant:
    logger.info("---*--- Creating Assistant ---*---")

    introduction = "Hi, I'm an AI Assistant that uses function calling to answer questions.\n"
    introduction += "Select the tools from the sidebar and ask me questions."

    description = dedent(
        """\
    You are a function calling AI model with access to various tools. Use your tools to assist the user in the best way possible.
    """
    )

    instructions = [
        "When the user asks a question, think how you can use your tools to answer the question.",
        "Don't make assumptions about what values to plug into functions.",
        "You may use agentic frameworks for reasoning and planning to help with user query.",
        "Analyze the results once you get them and call another function if needed.",
        "Your final response should directly answer the user query with an analysis or summary of the results of function calls.",
        "Format you response using markdown and provide a concise and relevant answer.",
        "Prefer to use bullet points for lists and tables for tabular data.",
    ]

    tools: List[Any] = []
    if web_search:
        tools.append(DuckDuckGo())
    if exa_search:
        tools.append(ExaTools())
    if yfinance:
        tools.append(YFinanceTools(stock_price=True, stock_fundamentals=True, analyst_recommendations=True))

    assistant = Assistant(
        description=description,
        instructions=instructions,
        tools=tools,
        show_tool_calls=True,
        debug_mode=debug_mode,
    )
    assistant.add_introduction(introduction)
    return assistant


def main() -> None:
    logger.info("---*--- Running App ---*---")

    # Sidebar checkboxes for selecting tools
    st.sidebar.markdown("### Select Tools")
    st.session_state["selected_tools"] = []

    web_search = st.sidebar.checkbox("Web Search", value=True, on_change=clear_assistant)
    exa_search = st.sidebar.checkbox("Exa Search", value=False, on_change=clear_assistant)
    yfinance = st.sidebar.checkbox("YFinance", value=False, on_change=clear_assistant)

    if not web_search and not exa_search and not yfinance:
        st.sidebar.warning("Please select at least one tool")

    # if web_search:
    #     st.session_state["selected_tools"].append("web_search")
    # if exa_search:
    #     st.session_state["selected_tools"].append("exa_search")
    # if yfinance:
    #     st.session_state["selected_tools"].append("yfinance")

    # Get the assistant
    assistant: Assistant
    if "assistant" not in st.session_state or st.session_state["assistant"] is None:
        assistant = create_assistant(
            web_search=web_search,
            exa_search=exa_search,
            yfinance=yfinance,
            debug_mode=True,
        )
        st.session_state["assistant"] = assistant
    else:
        assistant = st.session_state["assistant"]

    # Load existing messages
    assistant_chat_history = assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me anything..."}]

    # Prompt for user input
    if prompt := st.chat_input():
        st.session_state["messages"].append({"role": "user", "content": prompt})

    # Display existing chat messages
    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # If last message is from a user, generate a new response
    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            response = ""
            resp_container = st.empty()
            for delta in assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)

            st.session_state["messages"].append({"role": "assistant", "content": response})

    st.sidebar.markdown("---")
    if st.sidebar.button("New Run"):
        clear_assistant()
        st.rerun()


main()
