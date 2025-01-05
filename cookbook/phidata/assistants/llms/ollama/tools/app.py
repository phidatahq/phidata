import nest_asyncio
import streamlit as st
from phi.assistant import Assistant
from phi.utils.log import logger

from assistant import get_function_calling_assistant  # type: ignore

nest_asyncio.apply()

st.set_page_config(
    page_title="Local Function Calling",
    page_icon=":orange_heart:",
)
st.title("Local Function Calling with Ollama")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def restart_assistant():
    logger.debug("---*--- Restarting Assistant ---*---")
    st.session_state["local_assistant"] = None
    st.session_state["local_assistant_run_id"] = None
    if "llm_updated" in st.session_state:
        if "ddg_search_enabled" in st.session_state:
            st.session_state["ddg_search_enabled"] = False
        if "tavily_search_enabled" in st.session_state:
            st.session_state["tavily_search_enabled"] = False
        if "yfinance_tools_enabled" in st.session_state:
            st.session_state["yfinance_tools_enabled"] = True
        del st.session_state["llm_updated"]
    st.rerun()


def main() -> None:
    # Get LLM id
    llm_id = st.sidebar.selectbox("Select LLM", options=["hermes2pro-llama3", "llama3"]) or "hermes2pro-llama3"
    # Set llm in session state
    if "llm_id" not in st.session_state:
        st.session_state["llm_id"] = llm_id
    # Restart the assistant if llm_id changes
    elif st.session_state["llm_id"] != llm_id:
        st.session_state["llm_id"] = llm_id
        st.session_state["llm_updated"] = True
        restart_assistant()

    # Sidebar checkboxes for selecting tools
    st.sidebar.markdown("### Select Tools")

    # Add yfinance_tools_enabled to session state
    if "yfinance_tools_enabled" not in st.session_state:
        st.session_state["yfinance_tools_enabled"] = True
    # Get yfinance_tools_enabled from session state if set
    yfinance_tools_enabled = st.session_state["yfinance_tools_enabled"]
    # Checkbox for enabling web search
    yfinance_tools = st.sidebar.checkbox("Yfinance", value=yfinance_tools_enabled)
    if yfinance_tools_enabled != yfinance_tools:
        st.session_state["yfinance_tools_enabled"] = yfinance_tools
        restart_assistant()

    # Add ddg_search_enabled to session state
    if "ddg_search_enabled" not in st.session_state:
        st.session_state["ddg_search_enabled"] = False
    # Get ddg_search_enabled from session state if set
    ddg_search_enabled = st.session_state["ddg_search_enabled"]
    # Checkbox for enabling web search
    ddg_search = st.sidebar.checkbox("DuckDuckGo Search", value=ddg_search_enabled)
    if ddg_search_enabled != ddg_search:
        st.session_state["ddg_search_enabled"] = ddg_search
        restart_assistant()

    # Get the assistant
    local_assistant: Assistant
    if "local_assistant" not in st.session_state or st.session_state["local_assistant"] is None:
        logger.info(f"---*--- Creating {llm_id} Assistant ---*---")
        local_assistant = get_function_calling_assistant(
            llm_id=llm_id,
            ddg_search=ddg_search_enabled,
            yfinance=yfinance_tools_enabled,
        )
        st.session_state["local_assistant"] = local_assistant
    else:
        local_assistant = st.session_state["local_assistant"]

    # Load existing messages
    assistant_chat_history = local_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me questions..."}]

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
            for delta in local_assistant.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    if st.sidebar.button("New Run"):
        restart_assistant()


main()
